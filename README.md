# crossborder
Shopeeの2国間差分

今後の開発フロー
0. 前提（現状）

GitHub リポ：crossborder（Codespacesで作業中）

ひな形ファイル一式あり

api/main.py は /health /sg_demand /match /score 実装済み

CI（ci.yml）あり、通る（No tests 許容版）

1. 依存 & ローカル実行の固定化

目的: Codespaces でも安定起動。将来の再現性を上げる。

ルート requirements.txt を確定（軽量版）

fastapi
uvicorn[standard]
pydantic
pandas
pyyaml
duckdb
rapidfuzz
python-dotenv
pytest


起動テスト（Codespacesターミナル）

python -m venv .venv && source .venv/bin/activate
python -m pip install -U pip && pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000


チェック:

GET /health が {"ok": true}

GET /sg_demand?cats=craft&days=30 が 2件返す

コミット：

git add -A
git commit -m "chore: lock minimal requirements & run instructions"
git push

2. OpenAPI → Dify 連携

目的: Dify からローカル/公開APIを呼ぶ。

openapi/crossborder.yaml の servers.url を 接続先に合わせて設定

ローカルDify→ローカルFastAPI（Docker→ホスト）なら：
http://host.docker.internal:8000

CodespacesでFastAPI公開URLを使うなら：
https://<id>-8000.app.github.dev に差し替え

Dify（Docker）を起動 → Tools → Add → OpenAPI → crossborder.yaml を登録

チェック:
Difyのツールテストで /health, /sg_demand が成功。

コミット：

git add openapi/crossborder.yaml
git commit -m "chore(openapi): configure server url for Dify"
git push

3. スコア通過の“見える化”（一時）

目的: ひとまず通過1件を作って動作確認。

方法A（推奨）: /score 呼び出し時に gm_threshold=0.3 を渡す

方法B: params/fees.yml の手数料/GSTを一時緩める

チェック:
POST /score のレスポンスが {"scored":[{...}]}（1件以上） になる。

4. メール通知（API or Difyノード）

方法1：FastAPIの通知エンドポイント（/notify/email）を使う

.env に SMTP を登録（Gmailなら App Password）

Dify Workflow の最後に HTTP Tool: /notify/email を置く

方法2：Dify の Email ノード（簡単）

ワークフロー最終ノードを「Email」にし、To と Subject を設定

本文は LLMノードの出力

チェック:
ワークフローを Run → メールが届く。

5. Dify Workflow（本番フロー）

目的: 1日1回のダイジェスト配信を自動化（JST）。

Trigger: Cron → 毎日 07:30 JST

Nodes:

Set Variables: cats=["craft","stationery","accessory"], days=30, gm_threshold=0.5

HTTP: /sg_demand → items

HTTP: /match（Body: { "sg_items": {{items.items}} }）→ matches

HTTP: /score（Body: {"matches": {{matches.matches}}, "gm_threshold": {{vars.gm_threshold}}}）→ scored

LLM（RAG有効）: ダイジェスト整形（500–700字、注意事項はKnowledge参照）

Email（または /notify/email）

チェック:
手動Runが成功 → Cron を ON。

6. GitHub 側“開発ログ”仕組み

目的: 開発履歴が残るように。

.github/ISSUE_TEMPLATE/devlog.md（日次ログIssue）

daily-devlog.yml（毎朝空Issueを作る、権限：issues: write）

コミット規約：Conventional Commits（feat:, fix: …）

チェック:
Actions → daily-devlog が動き、Dev Log: YYYY-MM-DD のIssueが作成される。

7. release-please でリリース運用（任意）

目的: CHANGELOG と GitHub Release を自動化。

.github/workflows/release.yml

name: release-please
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: write
  pull-requests: write
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: google-github-actions/release-please-action@v4
        with:
          release-type: simple
          package-name: crossborder


チェック:
push 後、リリースPRが自動で作成 → Merge でタグ & Release が作成。

8. 実データ化（Playwright差し替え）

目的: /sg_demand のダミーを実データ収集に変更。

依存追加（容量に注意）

pip install playwright
python -m playwright install chromium   # ブラウザDL（数百MB）


api/main.py の /sg_demand 内で

指定カテゴリの検索 → 価格p25/median、レビュー30日増、出品数などを抽出

当初は1サイト＆1カテゴリから開始（失敗を減らす）

チェック:
/sg_demand が実データを返し、以降の /match /score が通る。

容量節約したい場合は、先にローカル（Mac）でPlaywright、CodespacesはAPIだけでもOK。

9. マッチ精度強化（後追い）

目的: JP候補とのマッチを改善し、誤一致を減らす。

RapidFuzz だけ → テキスト＋属性（サイズ/素材）ペナルティを加点減点

画像類似を入れる場合：軽量な fastembed（埋め込み） or imagehash（近似）を追加

人手承認フラグ human_verified を matches に付け、次回以降は優先

チェック:
ダイジェストの誤検知が目に見えて減る（ログの「注意/NG」が少なくなる）。

10. 差分配信（スパム防止）

目的: 前日と差がない日はメールを短く、変化だけ通知。

DuckDBに直近の scored を保存（例：data/last_scored.duckdb）

今日の scored と比較 → 新規/しきい値跨ぎ/相場下落だけ LLM へ渡す

チェック:
「新着0件」の日は“要約1行のみ”になる。

11. 完成の定義（Doneの基準）

Dify Workflow が 毎朝07:30 JST に自動実行

メールに 新規合格（GM≥50%） と 注意/NG理由 が載る

GitHub の Actions（CI/Release/DevLog） が緑

リポに 日次ログIssue が蓄積

手元の fees.yml / shipping.yml を変えてもフローが壊れない

12. 代表トラブルと即対処
