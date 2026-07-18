# 保坂栄次 はてなブログ月別表示

はてなブログの記事を自動取得し、前月と今月を2列で表示するGitHub Pages用一式です。
2026年7月に動かすと「6月の情報」「7月の情報」が表示されます。8月になると自動的に「7月」「8月」へ切り替わります。

## 1. GitHubに新しいリポジトリを作る
1. GitHubにログインします。
2. 右上の「＋」→「New repository」を押します。
3. Repository nameに `hosaka-news` と入力します。
4. Publicを選びます。
5. 「Create repository」を押します。

## 2. ZIPの中身をアップロード
1. ZIPを解凍します。
2. リポジトリで「Add file」→「Upload files」を押します。
3. 解凍した中身をすべてアップロードします。
4. `Commit changes` を押します。

※ `.github` フォルダも必ずアップロードしてください。

## 3. 自動更新を最初に実行
1. 上部の「Actions」を押します。
2. 「はてなブログ記事を更新」を選びます。
3. 「Run workflow」→「Run workflow」を押します。
4. 1～2分後、緑色のチェックが付けば成功です。

## 4. GitHub Pagesを公開
1. 上部の「Settings」を押します。
2. 左側の「Pages」を押します。
3. Sourceを「Deploy from a branch」にします。
4. Branchを `main`、フォルダを `/(root)` にします。
5. 「Save」を押します。
6. 数分後に公開URLが表示されます。

例：`https://あなたのGitHub名.github.io/hosaka-news/`

## 5. Google Sitesに埋め込む
1. Google Sites編集画面で「挿入」→「埋め込む」。
2. 「URL」を選び、GitHub Pagesの公開URLを貼ります。
3. 「挿入」を押し、枠を下へ広げます。
4. 右上の「公開」を押します。

## 自動更新
6時間ごとに自動更新します。すぐ更新したい場合は、Actionsから「Run workflow」を押してください。
