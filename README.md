# food-photo-agent

在自己電腦上執行的 Discord agent。指定頻道有人傳食物照片，它用 `claude -p` 判斷並估算熱量，記進 Excel、存照片，再回覆上傳者與當日已攝取的熱量。

- 需求：`docs/requirements.md`
- 架構與設計決定：`docs/architecture.md`
- Discord 設定步驟：`docs/discord-server-setup.md`、`docs/discord-bot-setup.md`

agent 開著才會運作。關掉就不處理，重新開啟也不會補處理關掉期間傳的照片。

## 啟動

在專案資料夾（`C:\Users\samson\food-photo-agent`）打開終端機，輸入：

```
uv run food-agent
```

第一次執行 uv 會自動建立環境並安裝套件（Python 3.12）。看到這一行就表示連上了：

```
INFO food_agent.bot: 已連線：food-photo-agent#xxxx，只處理頻道 ...
```

關掉：在終端機按 `Ctrl + C`。

啟動前先決定好 `.env`（從 `.env.example` 複製）：`DISCORD_TOKEN`、`CHANNEL_ID`、`CLAUDE_MODEL`、`DATA_DIR`。缺哪一項，啟動時會直接告訴你。

## 使用者看到什麼

1. 在指定頻道傳照片：該則訊息上出現 ⏳（收到、排隊中）。
2. 處理完：⏳ 消失，出現 ✅（失敗是 ❌），並有一則「回覆」，內容是是不是食物、成份、重量、熱量，以及**當日已攝取熱量**（整個頻道今天的合計，不分人）。
3. 不是食物也會回覆、建檔、存照片，食物敘述欄寫「不是食物」，成份欄寫判定出來的東西。
4. 失敗時回覆「分析失敗，請再傳一次」，不建檔。

## log：處理過程看得到、也有記錄

每一步都會顯示在終端機，同時寫進 `DATA_DIR/agent.log`（單檔上限 5 MB，保留 3 份舊檔）。同一則訊息的紀錄開頭有同一個編號 `[#456789]`，用它可以把一則訊息從收到到完成的過程串起來：

```
INFO food_agent.bot: [#456789] 收到：上傳者 小明（42），2 張圖片，備註 4 字：'半碗就好'
INFO food_agent.bot: [#456789] 已排隊：處理中 0 則，等待中 1 則（含這一則）
INFO food_agent.bot: [#456789] 開始處理（在佇列裡等了 0.0 秒）
INFO food_agent.pipeline: [#456789] 下載完成：2 張，共 286 KB
INFO food_agent.analyzer: [#456789] 呼叫 claude -p（第 1/2 次，模型 sonnet，2 張照片）
INFO food_agent.analyzer: [#456789] claude -p 完成：耗時 8.1 秒，估算費用 $0.0142（牌價）
INFO food_agent.pipeline: [#456789] 分析結果：食物 生菜牛肉漢堡（成份 3 項），約 200 公克、450 大卡
INFO food_agent.pipeline: [#456789] 已存照片：photos/2026-10-15 12-30-45 生菜牛肉漢堡.jpg
INFO food_agent.pipeline: [#456789] 已寫入 Excel：2 列，當日已攝取熱量 450 大卡
INFO food_agent.bot: [#456789] 已回覆（168 字）
INFO food_agent.bot: [#456789] 完成：處理 8.3 秒，從收到算起共 8.3 秒
```

拒絕（格式不支援、檔案太大、排隊已滿）、分析不合格、Excel 寫不進去等情況都是 `WARNING` 或 `ERROR`。不會記錄 `DISCORD_TOKEN`、`claude` 的完整輸出，備註只留前 50 字。

## 資料放在哪

都在 `DATA_DIR` 底下：

```
DATA_DIR/
├─ food_log.xlsx     紀錄檔。新的一列加在最後，不會覆蓋
├─ photos/           照片，檔名 YYYY-MM-DD hh-mm-ss 食物名稱.jpg，同一秒撞名加 -2、-3
└─ agent.log         log 檔
```

Excel 欄位：日期時間、上傳者、食物敘述、成份、重量(公克)、熱量(大卡)、當日已攝取熱量(大卡)、照片存放位置。

**Excel 開著的時候 agent 寫不進去。** 終端機會印出 `[警告]` 並重試幾次，仍然不行就回覆「記錄檔現在寫不進去，這次沒有記錄」。不看資料時請把 Excel 關掉。

## 四段防護在哪裡

每一段都用這種註解包起來，開始與結束都標得出來：

```
# ==== 防護 N：名稱　開始 ====
...
# ==== 防護 N 結束 ====
```

每一段前面都有一行「沒有防護時的預設寫法」，防護段落再覆蓋它。所以**把某一段整段註解掉，程式照樣能跑**，只是少了那一層防護。一開始四段全部開著。

| 防護 | 檔案 | 約在第幾行 | 做什麼 |
|---|---|---|---|
| 防護 1：`claude -p` 的檔案範圍隔離 | `src/food_agent/analyzer.py` | 97 到 108 | 每則訊息建一個暫存資料夾，只放這一則的照片，`claude -p` 只能讀那裡，不能讀 `DATA_DIR` |
| 防護 2：上傳者文字只當資料 | `src/food_agent/analyzer.py` | 121 到 127 | 上傳者打的字只放進 `<uploader_note>` 標籤並截短，不接進指令 |
| 防護 3：檔名清洗 | `src/food_agent/storage.py` | 49 到 54 | 食物名稱當檔名前，去掉 `/`、`\`、`..`、冒號等，並確認路徑在照片資料夾裡 |
| 防護 4：Excel 公式字元處理 | `src/food_agent/ledger.py` | 69 到 72 | 以 `=`、`+`、`-`、`@` 開頭的文字，前面加單引號並標成文字格 |

行號是約數，改過程式後請重新查：

```
grep -nE "防護 [1-4]：.*開始|防護 [1-4] 結束" src/food_agent/*.py
```

註解掉某一段之後，建議跑一次測試看看哪些項目會失敗，那就是這一段原本擋住的事情：

```
uv run pytest
```

## 測試

```
uv run pytest
```

自動測試不連 Discord、不呼叫真的 `claude`。涵蓋 JSON 驗證、檔名清洗與撞名、Excel 往下加與當日加總、公式字元、排隊、四段防護的行為，以及整個處理流程。

## 注意事項

- `.env` 不可以 commit，裡面有 bot token。`DATA_DIR` 裡的照片、Excel、log 也不可以 commit。`.gitignore` 已經擋住 `.env`、`.env.*`（`.env.example` 除外）、`food-data/`、`data/`、`photos/`、`*.xlsx`。
- `DATA_DIR` 建議放在專案資料夾之外。放在裡面的話，啟動時會出現警告，提醒你確認它有被 `.gitignore` 擋住。
- 每處理一則訊息就會呼叫一次 `claude -p`（不合格時最多再試一次），用掉你自己 Claude 帳號的額度。能傳照片到那個頻道的人，就是能花你額度的人。
- 找不到頻道、bot 缺權限，啟動時會在終端機警告。
- 啟動後連上了，但有人傳照片完全沒反應：到 Developer Portal 的 Bot 頁，確認 **Message Content Intent** 是開著的。沒開的話 bot 收不到附件。

## 資料夾結構

```
src/food_agent/
├─ main.py        進入點：讀設定、啟動
├─ config.py      讀 .env、各種預設上限
├─ bot.py         Discord：收訊息、過濾、加反應、回覆
├─ queueing.py    排隊：一次只處理一則
├─ pipeline.py    處理一則訊息的流程：下載、分析、存照片、建檔、組回覆
├─ logs.py        log 設定：終端機加 agent.log，每則訊息一個 [#編號]
├─ analyzer.py    呼叫 claude -p（防護 1、防護 2）
├─ schema.py      JSON 格式與驗證
├─ storage.py     存照片、命名（防護 3）
├─ ledger.py      Excel 紀錄、當日加總（防護 4）
├─ replies.py     回覆文字
└─ models.py      共用的資料型別
tests/            自動測試
```
