import argparse

from pytubefix import YouTube, Channel


class ProgramArguments:

    def __init__(self):
        ap = argparse.ArgumentParser()
        ap.add_argument("-f", "--file", required=True,
                        help="path to input video file")
        ap.add_argument("-t", "--tracker", type=str, default="csrt")
        ap.add_argument("-o", "--output", type=str, default="output.txt")
        ap.add_argument("-r", "--ratio", type=int, default=5)
        ap.add_argument("-g", "--gray", type=bool, default=False)
        ap.add_argument("-d", "--delta", type=int, default=15)
        ap.add_argument("-T", "--title", type=str, required=False)
        ap.add_argument("-S" , "--smooth-sigma", type=int, default=5)
        ap.add_argument("-s", "--scene-threshold", type=int, default=30)
        ap.add_argument("-u", "--dry-run", action=argparse.BooleanOptionalAction, default=False)
        ap.add_argument("--debug", action=argparse.BooleanOptionalAction, default=False)
        ap.add_argument("-b", "--subtitle", required=False, type=str)
        ap.add_argument("-y", "--youtube-link", type=str, required=False)
        args = vars(ap.parse_args())
        self.file = args["file"]
        self.tracker = args["tracker"]
        self.output = args["output"]
        self.ratio = args["ratio"]
        self.delta = args["delta"]
        self.gray = args["gray"]
        self.title = args["title"]
        self.smooth_sigma = args["smooth_sigma"]
        self.scene_threshold = args["scene_threshold"]
        self.subtitle = args["subtitle"]
        self.youtube_link = args["youtube_link"]
        self.dry_run = args["dry_run"]
        self.debug = args["debug"]

    def youtube_channel(self):
        try:
            yt = YouTube(self.youtube_link)
            channel = Channel(yt.channel_url)
            return channel.vanity_url.split("www.")[1]
        except:
            return None


class Rectangle:
    final_width = 0
    final_height = 0

    def __init__(self, x1, x2, y1, y2, frame_number, ratio):
        self.x1 = float(x1)
        self.x2 = float(x2)
        self.y1 = float(y1)
        self.y2 = float(y2)
        self.frame_number = int(frame_number)
        self.ratio = float(ratio)

    @staticmethod
    def from_roi(roi, frame_number, ratio):
        return Rectangle(roi[0], roi[0] + roi[2], roi[1], roi[1] + roi[3], frame_number, ratio)



    def to_dict(self):
        return {
            "x1": self.x1,
            "x2": self.x2,
            "y1": self.y1,
            "y2": self.y2,
            "frame_number": self.frame_number,
            "ratio": self.ratio
        }

    def get_x1(self):
        return self.x1 * self.ratio

    def get_x2(self):
        return self.x2 * self.ratio

    def get_y1(self):
        return self.y1 * self.ratio

    def get_y2(self):
        return self.y2 * self.ratio

    def get_center_x(self):
        return int((self.x1 + self.x2) / 2)

    def get_point1_final(self):
        x1 = self.get_center_x() - Rectangle.final_width / self.ratio / 2
        return int(x1), int(0)

    def get_point2_final(self):
        x1 = self.get_center_x() + Rectangle.final_width / self.ratio / 2
        return int(x1), int(Rectangle.final_height / self.ratio)

    def get_point1(self):
        return int(self.get_x1()), int(self.get_y1())

    def get_point2(self):
        return int(self.get_x2()), int(self.get_y2())

    def get_point1_unscaled(self):
        return int(self.x1), int(self.y1)

    def get_point2_unscaled(self):
        return int(self.x2), int(self.y2)

    def get_frame_number(self):
        return self.frame_number


class Center:
    def __init__(self, x, y, frame_number):
        self.x = x
        self.y = y
        self.frame_number = frame_number

    @staticmethod
    def from_rect(rect: Rectangle):
        x = int((rect.get_x1() + rect.get_x2()) / 2)
        y = int((rect.get_y1() + rect.get_y2()) / 2)
        frame_number = rect.get_frame_number()
        return Center(x, y, frame_number)

    def get_x(self):
        return self.x

    def get_y(self):
        return self.y

    def get_frame_number(self):
        return self.frame_number

    def __str__(self):
        return f"X: {self.x}, Y: {self.y}, Frame: {self.frame_number}"


class Scene:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def get_start(self):
        return self.start

    def get_end(self):
        return self.end


class CenteredScene(Scene):
    def __init__(self, start, end, centers: list[Center]):
        super().__init__(start, end)
        self.centers = centers

    @staticmethod
    def from_rectangles(start, end, frames: list[Rectangle]):
        frames = sorted(frames, key=lambda x: x.get_frame_number())
        centers = list(map(lambda rect: Center.from_rect(rect), frames))
        result = CenteredScene(start, end, centers)
        return result

    def get_centers(self):
        return self.centers


    # serialize the data
    def to_json(self):
        return {
            "start": self.start,
            "end": self.end,
            "centers": [(center.get_x(), center.get_y(), center.get_frame_number()) for center in self.centers]
        }

    # deserialize the data
    @staticmethod
    def from_json(data):
        start = data["start"]
        end = data["end"]
        centers = [Center(x, y, frame_number) for x, y, frame_number in data["centers"]]
        return CenteredScene(start, end, centers)

    def __str__(self):
        return f"Start: {self.start}, End: {self.end}, Centers: {[str(center) for center in self.centers]}"
