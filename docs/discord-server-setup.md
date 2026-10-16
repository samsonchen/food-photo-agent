# Discord Server 設定步驟

這份文件帶你做三件事：

1. 建立一個你自己的 Discord Server（Server 就是一個社群空間，裡面有很多頻道）。
2. 建立一個頻道給這個 agent 用，並拿到它的 `CHANNEL_ID`。
3. 產生邀請連結，讓同組同學加入你的 Server，後面測試要用。

做完這份之後，接著做 `docs/discord-bot-setup.md`。

**關於畫面**：Discord 偶爾會改版。這份文件依官方說明和網路上的教學整理，部分按鈕名稱沒有在官方頁面逐字確認。如果你看到的畫面和文件不同，找名稱或意思相近的選項。Discord 畫面如果是中文，括號裡的英文可以當線索。

**事前準備**：

- Windows 電腦上安裝 Discord 桌面版並登入，或用瀏覽器打開 `https://discord.com/app` 登入。下面的步驟以桌面版為準。
- 如果你還沒有 Discord 帳號，先註冊一個。

---

## 一、建立你自己的 Server

1. 看畫面最左邊那一排圓形圖示，這一排是你加入的 Server 列表。
2. 找到這一排最下面的 **+** 按鈕（滑鼠移上去會顯示 Add a Server），點它。
3. 在跳出的視窗裡選 **Create My Own**（自己建立）。
4. 下一個畫面問你這個 Server 是給誰用的，選 **For me and my friends**（給我和我的朋友）。
5. 在 **Server Name** 欄位輸入名稱，例如 `food-photo-test`。
6. 圖示可以不傳，直接按右下角的 **Create**（建立）。

你應該看到：

- 最左邊那一排多了一個新圖示，就是你的 Server。
- 左邊的頻道列表有預設的頻道，例如 `#general`。

---

## 二、建立給 agent 用的頻道

agent 只會處理一個頻道的照片（見 `docs/architecture.md` 第 13 節），所以要建一個專用頻道。

1. 在左邊的頻道列表找到 **Text Channels**（文字頻道）這一行，點它右邊的 **+**（滑鼠移上去會顯示 Create Channel）。
2. **Channel Type**（頻道類型）選 **Text**（文字）。
3. **Channel Name**（頻道名稱）輸入 `food-photos`。Discord 會自動轉成小寫、空白變成 `-`。
4. **Private Channel**（私人頻道）的開關保持**關閉**。之後同學要在這個頻道傳照片，開著的話他們看不到。
5. 按 **Create Channel**。

你應該看到左邊頻道列表多了 `#food-photos`，點它，右邊會變成這個頻道的畫面。

---

## 三、拿到 CHANNEL_ID

`CHANNEL_ID` 是 Discord 給每個頻道的一組數字編號。agent 靠它知道要處理哪個頻道。要先打開「開發者模式」，右鍵選單裡才會出現複製編號的選項。

### 打開開發者模式（只需要做一次）

1. 點畫面左下角、你的名字旁邊的**齒輪圖示**，打開 **User Settings**（使用者設定）。
2. 在左邊的選單往下找 **Advanced**（進階），點它。
3. 把 **Developer Mode**（開發者模式）的開關打開。開關變成綠色打勾就是開啟了。
4. 按右上角的 **X** 或鍵盤的 **Esc** 離開設定。

### 複製 CHANNEL_ID

1. 在左邊的頻道列表，對著 `#food-photos` 按**滑鼠右鍵**。
2. 在選單最下面找 **Copy Channel ID**（複製頻道 ID），點它。
3. 不要選到 **Copy Link**（複製連結），那個複製出來的是網址，不是編號。

### 確認複製對了

1. 打開 Windows 的「記事本」。
2. 按 `Ctrl + V` 貼上。
3. 你應該看到**一長串純數字**，大約 18 到 19 位，例如 `1234567890123456789`。裡面不會有字母、`<`、`#` 或網址。

CHANNEL_ID 不算機密，但還是不要 commit 進 git（見下方第四節）。

---

## 四、把 CHANNEL_ID 存進 `.env`

`.env` 是放設定的純文字檔，agent 啟動時會讀它。這個檔案放在專案資料夾 `C:\Users\samson\food-photo-agent\` 裡，名字就是 `.env`。

專案裡目前還沒有這個檔案，所以要自己建立。

1. 打開「記事本」。
2. 貼上下面四行，把 `CHANNEL_ID=` 後面換成你剛剛複製的數字：

   ```
   DISCORD_TOKEN=
   CHANNEL_ID=（貼上你剛複製的數字，不要加引號或空白）
   CLAUDE_MODEL=sonnet
   DATA_DIR=C:\Users\samson\food-data
   ```

   `DISCORD_TOKEN=` 先留空，做 `docs/discord-bot-setup.md` 時再填。
3. 按 **檔案 → 另存新檔**。
4. 存檔位置選 `C:\Users\samson\food-photo-agent`。
5. **存檔類型**改成 **所有檔案 (\*.\*)**。
6. **檔案名稱**輸入 `.env`，按存檔。

**Windows 常見的坑**：如果存檔類型還是「文字文件」，檔案會變成 `.env.txt`，agent 找不到它。檔案總管預設會隱藏副檔名，所以不容易看出來。處理方式：打開檔案總管，上方選單點 **檢視 → 顯示 → 檔案副檔名**，確認檔名是 `.env`，不是 `.env.txt`。

### 確認 `.env` 不會被 commit

在這個對話裡輸入下面這行（開頭的 `!` 表示直接在你的電腦上執行）：

```
! git status
```

輸出裡**不應該**出現 `.env`。`.gitignore` 已經擋掉它了。如果出現了，先不要 commit，告訴我。

---

## 五、產生邀請連結，讓同學加入

1. 在左邊頻道列表最上面，點你的 **Server 名稱**（旁邊有向下的小箭頭），會展開一個選單。
2. 選 **Invite People**（邀請其他人）。
3. 跳出的視窗最下面有一行小字寫著連結的有效期限，旁邊有一個**齒輪圖示**或 **Edit invite link**（編輯邀請連結），點它。
4. 設定：
   - **Expire After**（期限）：選 **7 days**（7 天）。測試用，不需要永久有效。
   - **Max number of uses**（最多使用次數）：選你預計邀請的人數。選項是固定幾檔（例如 1、5、10、25、50、100），選剛好夠用的那一檔。你的同學人數：（待填）。
   - **Grant temporary membership**（授予臨時成員資格）：保持**關閉**。開著的話，同學離線後會被自動踢出。
5. 按 **Generate a New Link**（產生新連結）。
6. 按連結旁邊的 **Copy**（複製）。
7. 把連結傳給同學，可以用 LINE、Email 或當面。同學點開連結，按 **Accept Invite**（接受邀請）就能加入。

### 確認同學加入成功

- 請同學加入後，到 `#food-photos` 頻道打一句話。你應該在頻道裡看到他的訊息。
- 如果他看不到這個頻道，回到第二節確認 **Private Channel** 是關閉的。

### 為什麼要限制期限和次數

agent 處理的每一張照片，都會用到**你自己的 Claude 額度**。能進這個 Server、傳照片的人，就是能花你額度的人（見 `docs/architecture.md` 第 13 節）。所以：

- 只邀請你信任的人。
- 邀請連結不要貼到公開的地方。
- 測試結束後，把連結關掉：點 Server 名稱 → **Server Settings**（伺服器設定）→ 左邊選單的 **Invites**（邀請）→ 找到那條連結，按右邊的 **X** 刪除。

### 同學不需要的東西

同學只需要加入 Server、在頻道傳照片。**不需要**也**不應該**拿到 bot token、`.env` 或你的 Claude 帳號。

---

## 完成檢查

- [ ] 我有一個自己的 Server。
- [ ] 裡面有 `#food-photos` 頻道，不是私人頻道。
- [ ] 我已經複製 CHANNEL_ID，確認是一長串純數字。
- [ ] 專案資料夾裡有 `.env`，檔名不是 `.env.txt`，`CHANNEL_ID=` 後面有填數字。
- [ ] `git status` 裡沒有出現 `.env`。
- [ ] 邀請連結設了期限和次數，已經傳給同學。

下一步：`docs/discord-bot-setup.md`。
