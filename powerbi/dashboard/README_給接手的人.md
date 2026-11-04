# LearnMate Power BI 儀表板 — 接手說明

這個資料夾是自足的，裡面有你需要的全部東西：

| 檔案 | 是什麼 |
|---|---|
| `LearnMate_AI_Dashboard.pbix` | Power BI 報表（要美化的就是這個）|
| `LearnMate_PowerBI_Data.xlsx` | 報表的資料來源（18 張表）|

## 你要做的事：把介面做好看

但先做一個**必要的小設定**，不然打開會抓不到資料（因為原本的資料路徑是別台電腦的）。

### 第一步：重新指定資料來源（只做一次）

1. 用 **Power BI Desktop** 打開 `LearnMate_AI_Dashboard.pbix`
2. 上方「**常用 → 轉換資料 → 資料來源設定**」
3. 選到那個 Excel 來源 → 按「**變更來源**」→ 指到**這個資料夾裡的** `LearnMate_PowerBI_Data.xlsx`
4. 關掉後按「**重新整理**」

資料表名稱（StudentsTable、CourseHealthTable、WeakTopicsTable、RemedialCompareTable、TopicStatsTable…）和欄位都沒變，所以現有的圖表不會壞，只是換成最新資料。

### 第二步：美化（你的主場）

可以發揮的方向（對應專題三個頁籤）：

- **診斷總覽**：學生完成率、平均測驗正確率、弱點熱區
- **Quiz 弱點分析**：各知識點錯誤率（TopicStats）、學生弱點明細（WeakTopics）
- **補救與健康度**：補救前後對照（RemedialCompare，看 improvement_rate）、課程健康度（CourseHealth）

建議：統一配色、加 KPI 卡片、把 `error_rate`/`accuracy_rate`/`improvement_rate` 用百分比與顏色級距呈現、弱點用紅色提醒。

## 資料怎麼更新（之後需要時）

資料是從 Django 專案自動產生的，不用手動改 Excel。更新三步（在 GGWP 專案裡）：

```bash
cd myproject
python manage.py export_powerbi_json --output ../outputs/learnmate/learnmate_powerbi_data.json
cd ../powerbi
python build_workbook.py --input ../outputs/learnmate/learnmate_powerbi_data.json --output dashboard/LearnMate_PowerBI_Data.xlsx
```

然後 Power BI 按「重新整理」。詳細說明看上一層的 `powerbi/README.md`。

## 欄位對照（挑常用的）

- `course_health`：enrolled_students, lesson_completion_rate, average_quiz_accuracy_rate, weakness_mentions
- `topic_stats`：topic, error_rate（知識點錯誤率）, weakness_mentions
- `weak_topics`：topic, issue_description, severity（low/medium/high）
- `remedial_comparisons`：before_accuracy_rate, after_accuracy_rate, improvement_rate
- `student_course_metrics`：latest_score_percent, latest_score_change_percent, lesson_completion_rate
