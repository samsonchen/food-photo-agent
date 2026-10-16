# Discord Bot 設定步驟

這份文件帶你做這幾件事：

1. 在 Discord Developer Portal 建立一個 application 和 bot。
2. 打開 Message Content Intent。
3. 拿到 bot token。
4. 設定 bot 需要的權限，把它邀請進你自己的 Server。

先做完 `docs/discord-server-setup.md`，你要有自己的 Server，才有地方可以邀請 bot 進去。

名詞：

- **Developer Portal**：Discord 的開發者後台網站，在這裡建立和管理 bot。
- **application**：Developer Portal 裡的一個專案。bot 是 application 底下的一個功能。
- **bot**：Discord 上由程式操控的機器人帳號。這個 agent 就是用一個 bot 帳號在頻道裡收發訊息。
- **token**：bot 的密碼。程式拿著它，Discord 才會承認「這是你的 bot」。

> **重要：bot token 絕對不能貼給任何人、不能貼進這個對話、不能 commit。**
>
> 拿到 token 的人，可以用你的 bot 身分在你的 Server 裡做任何 bot 有權限做的事。token 只能放在你電腦上專案資料夾裡的 `.env` 檔，不能放在別的地方。細節見最後的「token 的規則」。

**關於畫面**：Developer Portal 偶爾會改版。這份文件依 Discord 官方的 Getting Started 文件整理，其中 **Message Content Intent** 的開關名稱和位置，官方那頁沒有逐字寫出，是依一般做法寫的。如果你看到的畫面和文件不同，找名稱或意思相近的選項。

---

## 一、建立 application 和 bot

1. 打開瀏覽器，進入 `https://discord.com/developers/applications`。
2. 如果要求登入，用你建立 Server 的那個 Discord 帳號登入。
3. 按右上角的 **New Application**（新增 application）。
4. **Name** 輸入 `food-photo-agent`。這個名字之後會變成 bot 在 Server 裡顯示的名字，可以之後再改。
5. 勾選同意 Discord 的開發者條款（如果有出現這個勾選框）。
6. 按 **Create**（建立）。

你應該看到進入這個 application 的 **General Information**（一般資訊）頁面，上面有 Application ID 等資料。

---

## 二、設定 Bot 頁面

1. 看畫面左邊的選單，點 **Bot**。
2. 如果頁面上有 **Add Bot** 的按鈕，按它並確認。新建立的 application 通常已經有 bot，沒有這個按鈕就不用管。

### 關掉 Public Bot

在 Bot 頁面找到 **Public Bot** 的開關，把它**關閉**。

這個開關關閉後，只有你自己（application 的擁有者）可以把 bot 加進 Server，別人不能自己拿連結把你的 bot 拉進他的 Server。

### 打開 Message Content Intent（一定要做）

1. 在 Bot 頁面往下捲，找到 **Privileged Gateway Intents** 這個區塊。
2. 找到 **Message Content Intent**，把它的開關**打開**。
3. 其他兩個（Presence Intent、Server Members Intent）**不要打開**，這個專案用不到。
4. 頁面下方如果跳出 **Save Changes**（儲存變更）的提示列，按它。
5. 重新整理頁面，確認 Message Content Intent 還是開著。

**為什麼一定要打開**：

- Intent 是 Discord 要求 bot 事先申報「我要收哪一類資料」的開關。
- 預設情況下，Discord 不會讓 bot 看到訊息的內容和附件。bot 收到的訊息是空的，看不到照片。
- 這個 agent 的工作就是讀頻道裡的照片附件。沒有打開這一項，agent 會顯示「已連線」，但有人傳照片時它完全沒有反應，而且程式本身不會報錯，很難找出原因。

---

## 三、拿到 bot token

> **提醒：token 只會顯示一次。複製之後要馬上貼到 `.env`。不要貼進這個對話，不要傳給任何人，不要截圖。**

1. 在 **Bot** 頁面找到 **Token** 區塊。
2. 按 **Reset Token**（重設 token）。
3. Discord 可能會要你再確認，例如輸入密碼或兩階段驗證碼，照畫面做。
4. 畫面上會出現一長串字元，這就是 token。按旁邊的 **Copy**（複製）。
5. **馬上**打開專案資料夾裡的 `.env`（用「記事本」打開）：
   - 檔案位置：`C:\Users\samson\food-photo-agent\.env`
   - 找到 `DISCORD_TOKEN=` 那一行，在 `=` 後面貼上 token（`Ctrl + V`），不要加引號或空白。
   - 按 `Ctrl + S` 存檔。
6. 關掉記事本。
7. 離開 Developer Portal 頁面前，不要對這一頁截圖或錄影。

如果 `.env` 還不存在，先回到 `docs/discord-server-setup.md` 的第四節建立它。

### 如果弄丟了或不確定有沒有複製成功

token 之後無法再查看。回到 Bot 頁面再按一次 **Reset Token**，會產生新的 token，舊的立刻失效。再複製、貼進 `.env` 一次。

### 確認 `.env` 沒有被 commit

在這個對話輸入下面這行（開頭的 `!` 表示直接在你的電腦上執行，結果不會經過我）：

```
! git status
```

輸出裡**不應該**出現 `.env`。如果出現了，先不要 commit，告訴我檔名就好，**不要貼 token**。

---

## 四、設定權限，邀請 bot 進你的 Server

這個專案的 bot 只需要四個權限：

| 權限 | 為什麼需要 |
|---|---|
| **View Channels** | 看得到頻道，才收得到照片 |
| **Send Messages** | 回覆分析結果 |
| **Read Message History** | 用「回覆」功能指向原本那則照片訊息 |
| **Add Reactions** | 在照片訊息上加 ⏳（收到）、✅（完成）、❌（失敗）反應 |

**不要**勾 Administrator（管理員）或其他權限。權限越少，bot 的 token 萬一外流，別人能做的事越少。

### 設定安裝方式

1. 在 Developer Portal 左邊的選單點 **Installation**。
2. 找到 **Installation Contexts**，只保留 **Guild Install**（安裝到 Server）打勾。**User Install**（安裝到個人帳號）取消勾選。
3. 找到 **Install Link**，選 **Discord Provided Link**（Discord 提供的連結）。
4. 往下找到 **Default Install Settings**（預設安裝設定）的 **Guild Install** 區塊：
   - **Scopes**（範圍）：加入 **bot**。其他的（例如 `applications.commands`）這個專案用不到，有預設勾選的可以留著，不影響。
   - 選了 `bot` 之後，會出現 **Permissions**（權限）選單，勾選上面表格的四項：**View Channels**、**Send Messages**、**Read Message History**、**Add Reactions**。
5. 如果頁面下方有 **Save Changes**，按它。

### 邀請 bot

1. 回到 **Installation** 頁面，複製上方的 **Install Link**（一個 `https://discord.com/oauth2/authorize?...` 的網址）。這個連結本身不是機密，但不需要傳給別人。
2. 把它貼到瀏覽器網址列，按 Enter。
3. 畫面會問你要把 bot 加到哪裡。選 **Add to server**（加到 Server），在下拉選單選你的 Server，按 **Continue**（繼續）。
4. 確認權限清單只有你勾的四項，按 **Authorize**（授權）。
5. 如果出現「我不是機器人」的驗證，照畫面完成。

### 確認 bot 進來了

1. 回到 Discord，打開你的 Server。
2. 看畫面最右邊的成員列表。你應該看到 `food-photo-agent`，旁邊有 **APP**（或 **BOT**）的標籤。
3. 因為 agent 還沒啟動，它現在顯示**離線**，這是正常的。
4. 頻道裡通常會跳出一則歡迎訊息，說 bot 加入了 Server。

### 讓 bot 只能看到 `#food-photos`（選做）

agent 只處理 `CHANNEL_ID` 那個頻道，其他頻道的訊息它會忽略。如果你還想從 Discord 的權限上也擋掉，可以這樣做：

1. 對 `#general`（或其他不想讓 bot 進入的頻道）按滑鼠右鍵，選 **Edit Channel**（編輯頻道）。
2. 左邊選 **Permissions**（權限）。
3. 在 **Roles/Members** 旁邊按 **+**，加入 `food-photo-agent`。
4. 找到 **View Channel**（檢視頻道），點它變成紅色的 **X**（拒絕）。
5. 按 **Save Changes**。

每個你不想讓 bot 看到的頻道都要各做一次。

---

## 完成檢查

- [ ] Developer Portal 裡有 `food-photo-agent` 這個 application。
- [ ] Bot 頁面的 **Public Bot** 是關閉的。
- [ ] Bot 頁面的 **Message Content Intent** 是開啟的，重新整理後還是開著。
- [ ] 我已經複製 token，貼進 `.env` 的 `DISCORD_TOKEN=` 後面，存檔。
- [ ] `git status` 裡沒有出現 `.env`。
- [ ] Server 的成員列表有 `food-photo-agent`，標籤是 APP 或 BOT，目前離線。
- [ ] bot 的權限只有 View Channels、Send Messages、Read Message History、Add Reactions。

### 如果 bot 已經邀請進 Server，但當時沒有勾 Add Reactions

不用重新邀請，直接補開這一項：

1. 在 Discord 點 Server 名稱 → **Server Settings**（伺服器設定）→ 左邊選 **Roles**（身分組）。
2. 點 `food-photo-agent` 這個身分組。
3. 切到 **Permissions**（權限）分頁，找到 **Add Reactions**（新增反應），把開關打開。
4. 按 **Save Changes**。

如果你把 `#food-photos` 的頻道權限另外設定過（見上面「讓 bot 只能看到 `#food-photos`」），也要確認那個頻道沒有把 bot 的 Add Reactions 設成拒絕。

四項設定（`DISCORD_TOKEN`、`CHANNEL_ID`、`CLAUDE_MODEL`、`DATA_DIR`）都填好之後，Discord 這邊就設定完成了。等程式寫好、啟動 agent，bot 才會變成上線。

---

## token 的規則

- **只能放在 `.env`**，位置是 `C:\Users\samson\food-photo-agent\.env`。
- **不能貼給任何人**，包含同學、朋友、客服、網路論壇。
- **不能貼進這個對話**（Claude Code）。需要告訴我設定完成，只說「token 已經放進 .env」就好。也請不要叫我打開或印出 `.env` 的內容。
- **不能 commit**。`.gitignore` 已經擋掉 `.env`，但每次 commit 前還是用 `git status` 確認一次。
- **不能放進程式碼、README、`docs/` 裡的文件、截圖、LINE 或 Google 文件的筆記**。
- **同學不需要 token**。他們只是在頻道傳照片，邀請連結（見 `docs/discord-server-setup.md`）和 token 是兩回事。

### 如果 token 外流了（貼錯地方、被 commit、被截圖）

1. **立刻**回到 Developer Portal → **Bot** → 按 **Reset Token**。舊的 token 馬上失效。
2. 把新的 token 貼進 `.env`，存檔。
3. 如果舊 token 已經被 commit 或 push 到 GitHub：先做上面兩步。光是把檔案從 git 刪掉不夠，因為歷史紀錄裡還找得到，所以重設 token 才是關鍵。之後再告訴我，一起處理 git 紀錄。
4. 到 Server 的成員列表和頻道裡看一下，有沒有 bot 發出你不認得的訊息。

---

## 依據

- Discord 官方 Getting Started：https://docs.discord.com/developers/quick-start/getting-started
