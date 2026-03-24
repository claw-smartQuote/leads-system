tell application "Calendar"
    tell calendar "日曆"
        set myEvents to every event whose summary contains "🚗"
        repeat with evt in myEvents
            delete evt
        end repeat
        return "刪除了 " & (count of myEvents) & " 個事件"
    end tell
end tell