# NEXT_WORK_ORDER

- STATUS: CREATED_NOT_DISPATCHED
- FROM: STUDENT-MAIN Brain  TO: MAIN Own Worker（唯一 actor）
- GIT_STATUS: 本地 git 已初始化（branch main）；**尚未設定 GitHub 遠端**

## 待辦
1. 學生授權後：在學生 GitHub 建立 `ntust-nasa-ai-lab` 儲存庫，`git remote add origin …`、`git push -u origin main`，讓 ChatGPT Brain 可從 GitHub 讀取審查。
2. （可選 MORE，各自另開有界 Milestone）美觀調整／雙 Engine 對照／方法比較（不同參考視窗敏感度）／真正 LLM API／部署。

- 資料：僅 `data/FD001/*`（唯讀）
- 允許：git remote、push；禁止：修改 `data/`、改寫歷史、force push
- 證據：remote URL、`git log -1` SHA、GitHub 頁面讀回
- STOP_IF：無 GitHub 權限或使用者未授權公開
- RETURN_TO：STUDENT-MAIN
