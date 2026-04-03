tell application "Calendar"
    tell calendar "港車北上保單"
        -- 刪除所有現有事件
        set allEvents to every event
        repeat with evt in allEvents
            delete evt
        end repeat
        return "已清除 " & (count of allEvents) & " 個舊事件"
    end tell
end tell