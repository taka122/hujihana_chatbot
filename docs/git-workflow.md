# Git ワークフロー ガイド

## 現在の状況確認（2026-03-31 時点）

### GitHub 上のブランチ一覧
| ブランチ名 | 状態 | 最新コミット |
|---|---|---|
| `main` | 存在する | 5536b9e |
| `develop` | 存在する | 5536b9e |
| `yamashita/develop` | ✅ 存在する | `a237423`（"initial commit on yamashita/branch"） |
| `yamashita/branch` | ❌ 存在しない | ― |

> **ポイント**: コミット `a237423` は GitHub の `yamashita/develop` に既に反映されています。
> `yamashita/branch` はまだ一度もリモートへ push されていないため、GitHub 上には存在しません。

---

## GitHub 上でブランチのファイルを確認する方法

### 方法 1：ブラウザの UI から
1. `https://github.com/taka122/hujihana_chatbot` を開く
2. 左上の **ブランチ選択ドロップダウン**（通常 `main` と表示されている）をクリック
3. 確認したいブランチ名（例: `yamashita/develop`）を選択
4. 選択したブランチ時点のファイル一覧が表示される

### 方法 2：URL を直接開く
```
https://github.com/taka122/hujihana_chatbot/tree/<ブランチ名>
```

例:
- `yamashita/develop` を見る:
  `https://github.com/taka122/hujihana_chatbot/tree/yamashita/develop`
- `yamashita/branch` を見る（push 後に有効）:
  `https://github.com/taka122/hujihana_chatbot/tree/yamashita/branch`

---

## `yamashita/branch` を GitHub に作成・更新する方法

### 状況：今いるブランチの内容を `yamashita/branch` という名前でリモートに push したい

現在 `yamashita/develop` にいる場合、`yamashita/branch` というリモートブランチを作るには以下の方法を使います。

#### 方法 A：今の `HEAD` をそのまま `yamashita/branch` として push（最短）
```powershell
git push -u origin HEAD:yamashita/branch
```
- ローカルにブランチを作らずに済む
- `yamashita/develop` と同じ内容が `yamashita/branch` としてリモートに作成される

#### 方法 B：ローカルにもブランチを作って push
```powershell
git switch -c yamashita/branch
git push -u origin yamashita/branch
```
- ローカルでも `yamashita/branch` ブランチが作られる
- 今後 `git push` だけで push できるようになる

---

## よくあるエラーと対処

### `error: src refspec yamashita/branch does not match any`

**原因**: `yamashita/branch` というローカルブランチが存在しない状態で `git push origin yamashita/branch` を実行した

**確認コマンド**:
```powershell
git branch          # ローカルブランチ一覧
git branch -r       # リモートブランチ一覧
git branch --show-current  # 今いるブランチ
```

**解決策**:
- 今いるブランチをそのまま push → `git push -u origin HEAD:yamashita/branch`（方法 A）
- ブランチを作ってから push → 方法 B を参照

---

## 現在地の確認方法（まず迷ったら）

```powershell
git status
git branch --show-current
git log --oneline -5
```
