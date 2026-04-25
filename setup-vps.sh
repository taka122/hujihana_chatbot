#!/usr/bin/env bash
# ============================================================================
# setup-vps.sh
#   Ubuntu VPS の初期セットアップスクリプト
#   - Docker (CE) と docker compose plugin のインストール
#   - UFW ファイアウォールの設定 (SSH / HTTP / HTTPS を許可)
#
# 使い方:
#   1. VPS に SSH で接続する:
#        ssh <user>@<vps-ip>
#   2. このスクリプトを VPS に転送する (ローカルから):
#        scp setup-vps.sh <user>@<vps-ip>:~/
#   3. VPS 上で実行権限を付与して実行する:
#        chmod +x setup-vps.sh
#        ./setup-vps.sh
#   4. スクリプト完了後、docker グループを有効化するため一度ログアウト&再ログイン:
#        exit
#        ssh <user>@<vps-ip>
#      その後、sudo なしで `docker ps` などが動作することを確認してください。
# ============================================================================

set -euo pipefail

echo "==> パッケージインデックスを更新します"
sudo apt-get update

echo "==> 必要な前提パッケージをインストールします"
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    git \
    ufw

echo "==> Docker の公式 GPG キーを追加します"
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "==> Docker の APT リポジトリを登録します"
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "==> パッケージインデックスを再度更新します"
sudo apt-get update

echo "==> Docker Engine と関連コンポーネントをインストールします"
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

echo "==> 現在のユーザー ($USER) を docker グループに追加します"
sudo usermod -aG docker "$USER"
# 注意: `newgrp docker` はスクリプト内では新しいシェルを起動してしまうため使わず、
#       スクリプト終了後に一度ログアウト/再ログインしてもらう方針にしています。

echo "==> UFW (ファイアウォール) のルールを設定します"
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

echo "==> UFW を有効化します (既に有効の場合はスキップされます)"
# 非対話的に有効化するため `--force` を使用
sudo ufw --force enable

echo "==> UFW の状態を表示します"
sudo ufw status verbose

echo ""
echo "============================================================"
echo " セットアップが完了しました"
echo " 一度ログアウトして再ログインすると、sudo なしで docker が使えます:"
echo "   exit"
echo "   ssh <user>@<vps-ip>"
echo "   docker ps"
echo "============================================================"
