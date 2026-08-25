# Recruit Copilot — the 25-second demo.
#
# Records the REAL shipped scripts against the fixtures in this folder. Nothing
# here is mocked: the PDF is rendered, both gates run on it, and the panel
# arithmetic is the same aggregate.py the /recruit:grade command calls.
#
#   brew install vhs ttyd     (or see https://github.com/charmbracelet/vhs)
#   vhs demo/demo.tape        (run from the repo root)

Output demo/recruit-copilot.gif

Require python3

Set Shell bash
Set FontSize 16
Set Width 1300
Set Height 570
Set Padding 20
Set TypingSpeed 18ms
Set Framerate 20
Set Theme "Dracula"

Hide
Type `export PS1="$ "` Enter
Type "clear" Enter
Show

Sleep 700ms
Type "# one posting in, one resume out. python renders it and measures the page." Enter
Sleep 600ms
Type "python3 skills/resume-builder/scripts/build.py demo/tailored.json --out /tmp/demo.pdf" Enter
Sleep 4500ms

Type "# then three independent judges score it, and python does the arithmetic." Enter
Sleep 600ms
Type "python3 skills/resume-grader/scripts/aggregate.py demo/panel.json | jq '{company,threshold,panel_avg,interview_votes,overall_pass,weakest_persona}'" Enter
Sleep 3500ms

Type "# 87.8 would pass almost anywhere. this employer's bar is 90, so it says no." Enter
Sleep 3500ms
