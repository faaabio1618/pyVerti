
# Parse argumentsS
param (
    [Parameter(Mandatory=$true)][string]$YouTubeLink,
    [Parameter(Mandatory=$true)][string]$Start,
    [Parameter(Mandatory=$true)][string]$Stop,
    [Parameter(Mandatory=$true)][string]$Title,
    [Parameter(Mandatory=$true)][string]$Subtitle,
    [Parameter(Mandatory=$true)][string]$Description
)

# Check for unknown options
$args | ForEach-Object {
    if ($_ -notmatch '^-[a-z]=')
    {
        Write-Error "Unknown option $_"
        exit 1
    }
}

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
    & yt-dlp.exe --quiet --progress $YouTubeLink -f "bestvideo/best" -o $InputPath --merge-output-format webm
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
