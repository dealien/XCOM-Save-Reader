rem Copies current XCom saves to a local user folder. Purely for testing purposes.
if [%~1]==[] goto :noargs
if [%~2]==[] goto :noargs
ROBOCOPY "%~1" "%~2" /MIR /XF README.txt
EXIT 0

:noargs
echo Expected two paths as arguments; switching to default paths.
ROBOCOPY "%HomePath%\Desktop\Gaming\OpenXcom\XPiratez\user\piratez" "user\piratez" /MIR /XF README.txt
EXIT 0
