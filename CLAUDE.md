# food-photo-agent

在我自己電腦上執行的 Discord agent：指定頻道有人傳食物照片，它用 `claude -p` 判斷並估算熱量，記進 Excel、存照片，再回覆上傳者與他當日已攝取的熱量。

## 開始任何工作前

先讀 `docs/architecture.md`。需求在 `docs/requirements.md`。程式要照架構文件寫，要改設計時先改文件，再改程式。

## 四段防護

架構文件第 12 節定義了四段防護：

1. 防護 1：`claude -p` 讀不到 `DATA_DIR`（在 `analyzer.py`）
2. 防護 2：上傳者打的字只當資料（在 `analyzer.py`）
3. 防護 3：名稱變成檔名前先清洗（在 `storage.py`）
4. 防護 4：寫進 Excel 的文字以 `=`、`+`、`-`、`@` 開頭時處理成純文字（在 `ledger.py`）

寫程式時：

- 每一段都用註解標出開始與結束，格式如下，四段各自獨立：

  ```
  # >>> 防護 3 開始：清洗檔名 >>>
  ...
  # <<< 防護 3 結束 <<<
  ```

- 四段一開始全部開啟。之後上課會逐段關掉做對照，所以不要擅自關掉、合併，或把一段拆散到別處。
- 沒有被要求時，不要新增或移除防護。

## 不可以 commit 的東西

- `.env` 不可以 commit。裡面有 `DISCORD_TOKEN`。只有 `.env.example`（值是佔位文字）可以 commit。
- `DATA_DIR` 裡的照片、Excel（`food_log.xlsx`）、log 都不可以 commit。
- 每次 commit 前用 `git status` 確認沒有這些檔案。
- 不要把 token 的值寫進程式、文件、log 或對話。
