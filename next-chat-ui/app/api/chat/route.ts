import { NextRequest, NextResponse } from "next/server";

import { Facility, loadFacilities } from "@/lib/facilities";

export const runtime = "nodejs";

type ChatRequest = {
  message?: string;
  apiKey?: string;
  history?: Array<{ role: "assistant" | "user"; text: string }>;
};

type Candidate = {
  id: string;
  name: string;
  city: string;
  serviceType: string;
  reason: string;
  sourceUrl: string;
  phone: string;
};

type GeminiEmbeddingResponse = {
  embeddings?: Array<{ values?: number[] }>;
  embedding?: { values?: number[] };
  error?: { message?: string };
};

type GeminiGenerateResponse = {
  candidates?: Array<{
    content?: { parts?: Array<{ text?: string }> };
  }>;
  error?: { message?: string };
};

const GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta";
const EMBEDDING_MODEL = "gemini-embedding-001";
const GENERATION_MODEL = "gemini-2.0-flash";

let docEmbeddingsCache: Array<{ facility: Facility; vector: number[] }> | null = null;

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const body = (await request.json()) as ChatRequest;
    const message = (body.message ?? "").trim();
    if (!message) {
      return NextResponse.json({ error: "message is required" }, { status: 400 });
    }

    const apiKey = (body.apiKey ?? process.env.GEMINI_API_KEY ?? "").trim();
    if (!apiKey) {
      return NextResponse.json(
        { error: "Gemini APIキーが未設定です。画面右側で設定してください。" },
        { status: 400 }
      );
    }

    const facilities = loadFacilities();
    const docEmbeddings = await getDocumentEmbeddings(apiKey, facilities);
    const queryVector = await embedQuery(apiKey, message);

    const ranked = docEmbeddings
      .map(({ facility, vector }) => ({
        facility,
        score: cosineSimilarity(queryVector, vector)
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 3);

    if (ranked.length === 0 || ranked[0].score <= 0) {
      return NextResponse.json({
        answer:
          "該当候補を十分な根拠で提示できませんでした（不明）。地域やサービス種別を具体化して再度お試しください。",
        candidates: [] as Candidate[]
      });
    }

    const history = Array.isArray(body.history) ? body.history : [];
    const answer = await generateAnswer(apiKey, message, history, ranked);
    const candidates: Candidate[] = ranked.map((item) => ({
      id: item.facility.id,
      name: item.facility.name,
      city: item.facility.city,
      serviceType: item.facility.serviceType,
      reason: `意味類似スコア: ${item.score.toFixed(3)}`,
      sourceUrl: item.facility.sourceUrl,
      phone: item.facility.phone
    }));

    return NextResponse.json({ answer, candidates });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "不明なエラーが発生しました。";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

async function getDocumentEmbeddings(
  apiKey: string,
  facilities: Facility[]
): Promise<Array<{ facility: Facility; vector: number[] }>> {
  if (docEmbeddingsCache) {
    return docEmbeddingsCache;
  }

  const requests = facilities.map((facility) => ({
    model: `models/${EMBEDDING_MODEL}`,
    taskType: "RETRIEVAL_DOCUMENT",
    title: facility.name,
    content: {
      parts: [{ text: buildFacilityDoc(facility) }]
    }
  }));

  const response = await geminiPost<GeminiEmbeddingResponse>(
    apiKey,
    `models/${EMBEDDING_MODEL}:batchEmbedContents`,
    { requests }
  );

  const embeddings = response.embeddings ?? [];
  if (embeddings.length !== facilities.length) {
    throw new Error(
      `埋め込み件数が不正です: expected=${facilities.length}, got=${embeddings.length}`
    );
  }

  docEmbeddingsCache = facilities.map((facility, index) => ({
    facility,
    vector: embeddings[index].values ?? []
  }));
  return docEmbeddingsCache;
}

async function embedQuery(apiKey: string, query: string): Promise<number[]> {
  const response = await geminiPost<GeminiEmbeddingResponse>(
    apiKey,
    `models/${EMBEDDING_MODEL}:embedContent`,
    {
      model: `models/${EMBEDDING_MODEL}`,
      taskType: "RETRIEVAL_QUERY",
      content: {
        parts: [{ text: query }]
      }
    }
  );
  const vector = response.embedding?.values ?? [];
  if (vector.length === 0) {
    throw new Error("クエリ埋め込みが空です。");
  }
  return vector;
}

async function generateAnswer(
  apiKey: string,
  message: string,
  history: Array<{ role: "assistant" | "user"; text: string }>,
  ranked: Array<{ facility: Facility; score: number }>
): Promise<string> {
  const historyText = history
    .slice(-6)
    .map((item) => `- ${item.role === "user" ? "ユーザー" : "アシスタント"}: ${item.text}`)
    .join("\n");

  const contextText = ranked
    .map(({ facility, score }) => `${buildFacilityDoc(facility)}\n類似スコア: ${score.toFixed(3)}`)
    .join("\n\n");

  const response = await geminiPost<GeminiGenerateResponse>(
    apiKey,
    `models/${GENERATION_MODEL}:generateContent`,
    {
      systemInstruction: {
        parts: [
          {
            text:
              "あなたは介護事業所案内アシスタントです。参照データだけを根拠に日本語で回答してください。" +
              "根拠が不足する情報は推測せず『不明』と明記してください。" +
              "最終確認は各事業所へ必要と短く添えてください。"
          }
        ]
      },
      contents: [
        {
          role: "user",
          parts: [
            {
              text:
                `相談内容:\n${message}\n\n` +
                `会話履歴(直近):\n${historyText || "なし"}\n\n` +
                `参照データ:\n${contextText}\n\n` +
                "出力形式:\n" +
                "1. 候補は最大3件\n" +
                "2. 各候補に理由を1行\n" +
                "3. 各候補に [ID:xxxx] を含める\n" +
                "4. 情報不足は『不明』と書く"
            }
          ]
        }
      ],
      generationConfig: {
        temperature: 0.2
      }
    }
  );

  for (const candidate of response.candidates ?? []) {
    for (const part of candidate.content?.parts ?? []) {
      if (part.text && part.text.trim()) {
        return part.text.trim();
      }
    }
  }
  throw new Error("Geminiから回答テキストを取得できませんでした。");
}

async function geminiPost<T>(
  apiKey: string,
  path: string,
  payload: Record<string, unknown>
): Promise<T> {
  const url = `${GEMINI_BASE_URL}/${path}?key=${encodeURIComponent(apiKey)}`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store"
  });

  const rawText = await response.text();
  let parsed: T | { error?: { message?: string } };
  try {
    parsed = JSON.parse(rawText) as T;
  } catch {
    throw new Error(`GeminiレスポンスのJSON解析に失敗しました: ${rawText}`);
  }

  if (!response.ok) {
    const message =
      (parsed as { error?: { message?: string } }).error?.message ?? rawText;
    throw new Error(`Gemini APIエラー(${response.status}): ${message}`);
  }

  if ((parsed as { error?: { message?: string } }).error?.message) {
    throw new Error((parsed as { error?: { message?: string } }).error?.message);
  }

  return parsed as T;
}

function buildFacilityDoc(facility: Facility): string {
  return (
    `[ID:${facility.id}]\n` +
    `名称: ${facility.name}\n` +
    `サービス: ${facility.serviceType}\n` +
    `地域: ${facility.prefecture}${facility.city}\n` +
    `住所: ${facility.address}\n` +
    `営業時間: ${facility.businessHours}\n` +
    `特徴: ${facility.features.join(", ")}\n` +
    `電話: ${facility.phone}\n` +
    `更新日: ${facility.lastUpdated}\n` +
    `ソース: ${facility.sourceUrl}`
  );
}

function cosineSimilarity(left: number[], right: number[]): number {
  if (left.length === 0 || right.length === 0 || left.length !== right.length) {
    return 0;
  }

  let dot = 0;
  let leftNorm = 0;
  let rightNorm = 0;
  for (let i = 0; i < left.length; i += 1) {
    dot += left[i] * right[i];
    leftNorm += left[i] * left[i];
    rightNorm += right[i] * right[i];
  }
  if (leftNorm === 0 || rightNorm === 0) {
    return 0;
  }
  return dot / (Math.sqrt(leftNorm) * Math.sqrt(rightNorm));
}

