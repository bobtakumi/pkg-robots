# 指示書: DGX Spark 上の LLM-jp-4 への接続情報を収集する

> **この文書の使い方**: これは *別マシン*（自宅で、DGX Spark 上の LLM-jp-4 に接続している既存アプリが動いている Mac）で
> Claude Code に渡す指示書です。Claude Code はこの指示に従い、既存アプリの設定と実通信を調べ、
> **末尾§7の「成果物テンプレート」を埋めた Markdown を出力**してください。
> その成果物を pkg_robots 側（別プロジェクト）に持ち帰り、config.toml を書き換えて本番接続します。

---

## 1. 背景（なぜこの情報が要るか）

`pkg_robots` は Obsidian の Personal Knowledge Garden に対する **Connector robot**（ノート間のリンク候補を LLM に判定させ、週次で提案レポートを出す）です。
4段のパイプライン `index → candidates → judge → report` から成り、プロトタイプはローカルで動作実証済み。残るは **判定 LLM を DGX Spark 上の LLM-jp-4 に繋ぐ工程（M6）**だけです。

pkg_robots が知りたいのは次の2つに集約されます:

- **判定エンドポイント**: LLM-jp-4 に、どの URL・どのモデル名・どの認証で、どんな API 形式で話しかければよいか。JSON を安定して返せるか。
- **埋め込みの所在**: 埋め込みモデル（現在プロトタイプは `bge-m3`）を DGX 側でも提供できるのか、それとも作業機側でホストし続けるのか。

この指示書の目的は、**憶測でなく既存アプリの実設定と実際の1往復から、これらを確定させる**ことです。

## 2. pkg_robots がエンドポイントに送るリクエストの形（重要・互換性判定の基準）

pkg_robots の judge クライアントは **OpenAI 互換の `POST {base}/chat/completions`** を前提にしています。送る本体はおおよそ次の形です:

```json
{
  "model": "<モデル名>",
  "messages": [
    {"role": "system", "content": "<Connector 判定の system プロンプト>"},
    {"role": "user", "content": "<zettel と文献チャンクを並べた本文>"}
  ],
  "temperature": 0.1
}
```

期待するレスポンスは `choices[0].message.content` に、次のような **JSON 文字列**が入っていること:

```json
{"verdict":"link|skip","relation":"根拠|具体例|反例|同型パターン|発展",
 "evidence_zettel":"…","evidence_lit":"…","reason":"…","confidence":1-5}
```

→ したがって調査では「この形式で話しかけて、content に妥当な JSON が返るか」を**実際に試して**ください（§5）。

埋め込みについて、pkg_robots のプロトタイプは Ollama 形式 `POST {base}/api/embed`（`{"model","input":[...]}`）を使っています。
DGX 側の埋め込み API が OpenAI 形式 `/v1/embeddings` の場合はクライアント側の小改修が要るので、**どちらの形式か**を必ず記録してください。

## 3. 調査手順（既存アプリ起点・読み取りのみ）

**既存アプリを変更しないこと。** 設定の読み取りと、疎通確認の GET/POST のみ行う。

1. **既存アプリを特定する** — DGX 上の LLM-jp-4 に繋いでいるアプリのリポジトリ/ディレクトリを見つけ、何であるかを一言で記録。
2. **接続設定の在処を洗う** — そのアプリの設定ファイル・環境変数・`.env`・docker-compose・起動スクリプト等から、次を抽出:
   - ベース URL（ホスト名/IP とポート。例 `http://dgx-spark.local:8000`）
   - API パス（`/v1/chat/completions` 等）
   - モデル名として渡している文字列
   - 認証方式（API キーの有無・ヘッダ名。**キーの値そのものは成果物に書かない**。§6）
3. **サービングスタックを判定する** — DGX 上で LLM-jp-4 を配信しているのは何か（**vLLM / Ollama / TGI / llama.cpp / SGLang / その他**）。分かる範囲でバージョンも。
   - 判定のヒント: `/v1/models` を叩く、プロセス名・コンテナ名・起動コマンド・ログのバナーを見る。
   - これが **JSON 構造化出力の可否**を左右する（vLLM = guided decoding / JSON schema、Ollama = `format: json`、等）。
4. **モデルの素性を確認する** — LLM-jp-4 の正確な変種・パラメータ規模・量子化（例: `llm-jp-4-...-instruct`, AWQ/GGUF Q4 等）、コンテキスト長、最大出力トークン。
   - `/v1/models` の応答、モデルカード、起動時の引数、ログから。
5. **DGX への到達性** — その Mac から DGX へどう到達しているか（同一 LAN / VPN / SSH ポートフォワード / Tailscale 等）。DGX は常時起動か。**pkg_robots が動く別マシンからも同じ URL で届くのか**（localhost 固定でないか、ホスト名/IP で外部公開されているか）。
6. **埋め込みモデルの有無** — DGX 側（または同じ配信基盤）で埋め込みモデルを提供しているか。あればモデル名と API 形式（`/v1/embeddings` か `/api/embed` か）。無ければ「埋め込みは作業機側でホスト継続」と結論づけてよい。

## 4. 判断してほしい設計上の問い（O1・O10）

- **O1（分担）**: 埋め込みも DGX に寄せるか、埋め込みは作業機（MBP）・判定は DGX の2拠点構成にするか。§3-6 の結果から推奨を1つ述べる。
- **O10（構成）**: 上記スタックで **JSON をどれだけ確実に返せるか**。guided decoding / JSON mode / tool calling のどれが使えるか。使えるなら pkg_robots はそれを使って出力を強制できる。

## 5. 疎通テスト（実際に1往復させて生ログを取る）

抽出した URL・モデル名・認証で、**pkg_robots が送るのと同じ形**を1回投げて、生レスポンスを取得してください。以下は雛形（URL・モデル名・キーは実値に置換。キーは環境変数経由にして履歴に残さない）:

```sh
curl -s "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  ${API_KEY:+-H "Authorization: Bearer $API_KEY"} \
  -d '{
    "model": "'"$MODEL"'",
    "messages": [
      {"role":"system","content":"あなたは JSON のみを返す判定器です。必ず {\"verdict\":\"link|skip\",\"reason\":\"…\",\"confidence\":1-5} の形だけを返す。"},
      {"role":"user","content":"zettel: エージェント = モデル + ハーネス / 文献: ハーネスとはモデルという動力を現実タスクに伝達する周辺機構の総体。これらは繋ぐべきか？"}
    ],
    "temperature": 0.1
  }'
```

- 返ってきた **content が素の JSON か**（コードフェンスや前置きが付かないか）、`verdict`/`confidence` が入るかを確認。
- 可能なら「JSON を強制するオプション」（vLLM の `guided_json`/`response_format`、Ollama の `format:"json"` 等）を付けた版も1回試し、挙動差を記録。
- 埋め込み API があれば、それも1回叩いてベクトル次元数を記録（`/v1/embeddings` か `/api/embed` か明記）。

## 6. 取り扱いの注意（セキュリティ）

- **API キー等の秘密の値は成果物 Markdown に書かない。** 「Bearer トークン必要／`~/.config/....env` の `LLMJP_API_KEY` に格納」のように**存在と供給方法だけ**記す。実値は後で pkg_robots の config に直接入れる。
- curl のキーは環境変数（`export API_KEY=...`）で渡し、シェル履歴やログに平文で残さない。
- 既存アプリの設定は**読むだけ**。書き換え・再起動はしない。

## 7. 成果物テンプレート（これを埋めた Markdown を出力する）

```markdown
# DGX Spark / LLM-jp-4 接続情報（pkg_robots 用インテーク）

## 1. DGX 基本
- ホスト名/IP: 
- ポート: 
- 到達経路（LAN/VPN/Tailscale 等）: 
- 常時起動か: 
- pkg_robots が動く別マシンから同一 URL で到達可能か: 

## 2. 判定エンドポイント（LLM-jp-4）
- ベース URL: 
- API パス: （例 /v1/chat/completions）
- OpenAI 互換か: 
- 認証方式: （値は書かない。供給方法のみ）
- サービングスタックとバージョン: 
- モデル名（API の model に渡す文字列）: 
- 変種/規模/量子化: 
- コンテキスト長 / 最大出力トークン: 
- JSON 構造化出力: guided decoding / json mode / tool calling の可否と使い方: 

## 3. 疎通テスト結果
- 送ったリクエスト（キー伏せ）: 
- 返った content（生・全文）: 
- content は素の JSON だったか / 崩れたか: 
- JSON 強制オプションを付けた場合の差: 

## 4. 埋め込みの所在
- DGX 側に埋め込みモデルはあるか: 
- あれば: モデル名 / API 形式（/v1/embeddings か /api/embed）/ ベクトル次元: 
- 推奨する分担（O1）: 埋め込みも DGX / 埋め込みは作業機・判定は DGX: 

## 5. 既存アプリからの根拠
- 既存アプリは何か: 
- 接続設定の在処（ファイルパス/環境変数名）: 
- そこから読み取った接続情報の要約: 

## 6. pkg_robots config.toml への落とし込み案
[embed]
  endpoint = ""
  model = ""
[judge]
  endpoint = ""
  model = ""
# 認証が要る場合の供給方法メモ: 
```

---

以上。**§7のテンプレートを埋めた Markdown 1枚**が最終成果物です。分からない項目は「不明・要確認」と明示し、憶測で埋めないでください。
