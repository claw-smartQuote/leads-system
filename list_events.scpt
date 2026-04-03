tell application "Calendar"
    tell calendar "日曆"
        set eventList to {}
        repeat with evt in every event
            try
                set s to summary of evt
                if s contains "保單" or s contains "到期" then
                    set end of eventList to s
                end if
            end try
        end repeat
        return eventList
    end tell
end tell