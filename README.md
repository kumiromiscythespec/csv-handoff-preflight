# CSV納品前チェック

**無料版 v0.1.0 · MIT**

[配布ZIP](https://github.com/kumiromiscythespec/csv-handoff-preflight/releases/tag/v0.1.0) を展開し、そのフォルダを開いて実行します。

CSVの列構成、空欄、キー重複、表計算ソフトで数式として解釈され得る値を確認し、入力値を載せないJSON/HTMLレポートを作ります。入力ファイルは変更せず、外部送信・アカウント登録・追加インストールはありません。Python 3.11以上が必要です。

```powershell
python -B handoff.py --schema examples/schema.json --output new-report examples/good.csv
python -B handoff.py --schema examples/schema.json --output review-report examples/review.csv
```

`--output`には未作成のフォルダ名を指定します。終了値0は指定検査のPASS、2は要確認です。JSONの`record`はCSVの論理レコード番号（ヘッダーが1）、`column`は1始まりです。引用符内の改行は別レコードとして数えません。UTF-8 BOMを許容します。CP932はschemaの`encoding`を明示的に`cp932`へ変えて使用してください。文字コードの自動推定や自動補正はしません。

制限は1ファイル5MB、10,000データ行、20ファイル、指摘表示200件です。列名・順序は完全一致、キーは文字列の完全一致です。負の数や先頭の空白・全角記号も保守的に要確認とするため、誤検出はあり得ます。入力を清浄化したCSVは生成しません。PASSは指定検査の結果であり、業務上の正しさ、すべての数式攻撃の検出、Excel等での安全性は保証しません。

Tablib 3.10.0のHTML出力でformatterが無視される現象に対し、`tablib_runtime.FormattedHTML.export_set(dataset)`および`export_book(databook)`を追加しました。CSVと同じformatter順でコピーをHTMLへ出力し、元データを保ちます。上流の`dataset.html`の挙動は変更しません。HTMLへ伏字を適用する場合はこの明示APIを使ってください。formatterは信頼するコードだけを登録し、全ての機密列への設定を別途確認してください。上流へ適用可能な変更案は`tablib-html-formatters.patch`です。外部への投稿はしていません。

同梱のCSVは動作確認用サンプルです。実務で使うときは、取引先の列名に合うように `examples/schema.json` をコピーして編集してください。

TablibのMITライセンス、著作権表示、AUTHORSを保持しています。依存物・商標の扱いは`THIRD_PARTY_NOTICES.txt`と`dependency-lock.json`を参照してください。この試作はTablib/Jazzbandの公式製品ではありません。

独自のコードはMITライセンスです。同梱のTablibには `vendor/TABLIB_LICENSE` の著作権表示とMITライセンスが適用されます。
