$YouTubeLink = Read-Host "Enter the YouTube link"
while ($YouTubeLink -notmatch '^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$')
{
    Write-Host "Invalid YouTube link. Please enter a valid link."
    $YouTubeLink = Read-Host "Enter the YouTube link"
}
$Start = Read-Host "Enter the start time (e.g. 00:00:00)"
while ($Start -notmatch '^\d{2}:\d{2}:\d{2}$')
{
    Write-Host "Invalid start time. Please enter a valid time in the format HH:MM:SS."
    $Start = Read-Host "Enter the start time (e.g. 00:00:00)"
}
$Stop = Read-Host "Enter the duration of the video (e.g. 00:00:00)"
while ($Stop -notmatch '^\d{2}:\d{2}:\d{2}$')
{
    Write-Host "Invalid stop time. Please enter a valid time in the format HH:MM:SS."
    $Stop = Read-Host "Enter the duration of the video (e.g. 00:00:00)"
}
$Title = Read-Host "Enter the title"
$Subtitle = Read-Host "Enter the subtitle"
$Description = Read-Host "Enter the description"

# Compute derived variables
$FileName = "$Title $Description"
$FileNameSafe = $FileName -replace ' ', '_'
$Ext = "webm"
$FilenameFromLink = $YouTubeLink.Split('=')[-1]
$InputPath = "walks\$FilenameFromLink\raw.$Ext"
$CutVideo = "walks\$FilenameFromLink\${FileNameSafe}_cut.mp4"
$CutLabeled = "walks\$FilenameFromLink\${FileNameSafe}_cut_labeld.mp4"
$CutLabeledInput = "walks\$FilenameFromLink\${FileNameSafe}_cut_labeled.txt"
$CroppedVideo = "walks\$FilenameFromLink\${FileNameSafe}_cropped_labeled.mp4"
$CroppedVideoInput = "walks\$FilenameFromLink\${FileNameSafe}_cropped.txt"


# Download video if it doesn't exist
if (-Not (Test-Path -Path $InputPath))
{
    Write-Output "Downloading video"
    & yt-dlp.exe $YouTubeLink -f "bestvideo*" -o $InputPath --merge-output-format webm --cookies-from-browser "firefox"
}
else
{
    Write-Output "Video already downloaded"
}

# Cut the video if it doesn't exist
if (-Not (Test-Path -Path $CutVideo))
{
    Write-Output "Cutting video"
    & ffmpeg -hwaccel cuda -nostats -hide_banner -loglevel error -y -i $InputPath -ss $Start -t $Stop $CutVideo
}
else
{
    Write-Output "Video already cut"
}

# Create label if it doesn't exist
if (-Not (Test-Path -Path $CutLabeledInput))
{
    Write-Output "Creating label"
    & .venv/Scripts/python.exe main.py --dry-run --file $CutVideo -y "$YouTubeLink" --title "$Title" --subtitle "$Subtitle" -o "$CutLabeledInput"
}
else
{
    Write-Output "Label already created"
}

# Create labeled video if it doesn't exist
if (-Not (Test-Path -Path $CutLabeled))
{
    Write-Output "Creating labeled video"
    Start-Process ffmpeg -ArgumentList "-hwaccel","cuda", "-nostats", "-hide_banner", "-loglevel", "error", "-y", "-ss", "00:00:00", "-i", "$CutVideo", "-an", "-filter_script:v:0", "$CutLabeledInput", "$CutLabeled" -NoNewWindow -Wait
}
else
{
    Write-Output "Labeled video already created"
}

# Create tracking if it doesn't exist
if (-Not (Test-Path -Path $CroppedVideoInput))
{
    Write-Output "Creating tracking"
    & .venv/Scripts/python.exe main.py -d 10 --file $CutVideo -y $YouTubeLink --title $Title --subtitle $Subtitle -o $CroppedVideoInput
}
else
{
    Write-Output "Tracking already created"
}

# Create cropped video if it doesn't exist
if (-Not (Test-Path -Path $CroppedVideo))
{
    Write-Output "Creating cropped video"
    & ffmpeg -hwaccel cuda -nostats -hide_banner -loglevel error -y -ss "00:00:00" -i $CutVideo -an -filter_script:v:0 $CroppedVideoInput $CroppedVideo
}
else
{
    Write-Output "Cropped video already created"
}
