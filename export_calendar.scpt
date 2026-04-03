tell application "Calendar"
    set output to ""
    tell calendar "港車北上保單"
        repeat with evt in every event
            set eventSummary to summary of evt
            set eventDate to start date of evt
            set output to output & eventSummary & "," & eventDate & "\n"
        end repeat
    end tell
    return output
end tell