tell application "Calendar"
    tell calendar "日曆"
        try
            set allEvents to every event
            set deletedCount to 0
            repeat with evt in allEvents
                try
                    set s to summary of evt
                    if s contains "保單" or s contains "到期" then
                        -- 先清除重複規則
                        set recurrence of evt to ""
                        -- 再刪除
                        delete evt
                        set deletedCount to deletedCount + 1
                    end if
                end try
            end repeat
            return "已清除重複並刪除 " & deletedCount & " 個事件"
        on error errMsg
            return "錯誤: " & errMsg
        end try
    end tell
end tell