import os
import json

import cv2
import numpy as np
from scenedetect import detect, ContentDetector
from scipy.ndimage import gaussian_filter1d

from lib.lib import RectangleTracker, ffmpeg_line
from lib.model import ProgramArguments, Rectangle, Scene, CenteredScene


class App:

    def __init__(self, arguments: ProgramArguments, frame_width, frame_height):
        self.file = arguments.file
        self.tracker = arguments.tracker
        self.output = arguments.output
        self.ratio = arguments.ratio
        self.delta = arguments.delta
        self.gray = arguments.gray
        self.title = arguments.title
        self.smooth_sigma = arguments.smooth_sigma
        self.scene_threshold = arguments.scene_threshold
        self.subtitle = arguments.subtitle
        self.youtube_link = arguments.youtube_link
        self.youtube_channel = arguments.youtube_channel()
        self.dry_run = arguments.dry_run
        self.debug = arguments.debug
        self.frame_width = frame_width
        self.frame_height = frame_height

    def collect_rectangles(self, vs) -> dict[int, Rectangle]:
        rectangles = self.handle_debug_input()
        if rectangles:
            return rectangles

        tracker = RectangleTracker(vs=vs, frame_width=self.frame_width, gray=self.gray, file=self.file,
                                   ratio=self.ratio,
                                   tracker=self.tracker)
        rectangles = tracker.track()
        self.handle_debug_output(rectangles)
        return rectangles

    def run(self, rectangles: {int: Rectangle}) -> list[CenteredScene]:
        scenes = self.cut_scenes(last_frame=max([rect.get_frame_number() for rect in rectangles.values()]))
        result = []
        for scene in scenes:
            rectangles_in_scene = [rect for frame_number, rect in rectangles.items() if
                                   scene.start <= frame_number < scene.end]

            centered_scene = CenteredScene.from_rectangles(scene.start, scene.end, rectangles_in_scene)
            result.append(centered_scene)

        return result

    def cut_scenes(self, last_frame: int) -> list[Scene]:
        """
        Detects scenes in a video file and returns a list frame indexes where the scene changes.
        :return:  List of frame indexes where the scene changes
        """
        scene_list = detect(self.file, ContentDetector(threshold=self.scene_threshold))
        if not scene_list:
            if self.debug:
                print("No scenes detected")
            return [Scene(0, last_frame + 1)]
        if self.debug:
            print([scene[0].frame_num for scene in scene_list])
        return [Scene(scene[0].frame_num, scene[1].frame_num) for scene in scene_list]

    def handle_debug_input(self):
        if self.debug and os.path.exists("debug.json"):
            with open("debug.json", "r") as file:
                centers = json.load(file)
                centers = {i: Rectangle(**center) for i, center in enumerate(centers)}
                return centers
        return None

    def handle_debug_output(self, centers: dict[int, Rectangle]):
        if self.debug:
            # save to debug.json the centers
            import json
            with open("debug.json", "w") as file:
                # centers is np array, we make it serializable
                serialized_centers = list(map(lambda x: x.to_dict(), centers.values()))
                json.dump(serialized_centers, file)

    def write(self, steps: list[tuple[int, int, int, int]]):
        self.write_to_file(steps)
        self.write_to_file_meta()

    def retrieve_steps(self, scene_centers: list[CenteredScene]) -> list[list[tuple[int, int, int, int]]]:
        steps = []
        for scene in scene_centers:
            scene_steps = []
            centers = scene.get_centers()
            total = len(centers)
            last_changed_frame = centers[0].get_frame_number()
            last_changed_x = centers[0].get_x()
            curr_x = centers[0].get_x()
            curr_y = centers[0].get_y()
            i = 0
            while i < total:
                if centers[i] is None:
                    raise Exception("Center is None")
                curr_x = centers[i].get_x()
                curr_y = centers[i].get_y()
                curr_n = centers[i].get_frame_number()

                changed = abs(curr_x - last_changed_x) > self.delta
                if changed and curr_n != last_changed_frame:
                    delta_frames = curr_n - last_changed_frame
                    center_step_x = (curr_x - last_changed_x) / delta_frames
                    for j in range(last_changed_frame, curr_n + 1):
                        last_changed_x += center_step_x
                        scene_steps.append((last_changed_x, 0, j, j))
                    last_changed_frame = curr_n + 1
                    last_changed_x = curr_x
                i = i + 1
            end = centers[-1].get_frame_number()
            if last_changed_frame <= end:
                for i in range(last_changed_frame, end + 1):
                    scene_steps.append((curr_x, curr_y, i, i))
            steps.append(scene_steps)
        return steps

    def smooth_steps(self, steps: list[tuple[int, int, int, int]]):
        xs = np.array(list(map(lambda step: step[0], steps)))
        # apply a gaussian filter to the centers
        new_xs = gaussian_filter1d(xs, sigma=self.smooth_sigma)
        new_steps = []
        for i, step in enumerate(steps):
            new_steps.append((int(new_xs[i]), step[1], step[2], step[3]))
        return new_steps

    def write_to_file(self, steps: list[tuple[int, int, int, int]]):
        frame_height = self.frame_height
        height = frame_height
        width = int(height * 9 / 16) + 1
        frame_width = self.frame_width
        with open(self.output, "w") as file:
            for step in steps:
                x, y, frame_start, frame_end = step
                file.write(ffmpeg_line(x, y, frame_start, frame_end, frame_width, frame_height, width, height))

    def write_to_file_meta(self):
        with open(self.output, "a", encoding="utf-8") as file:
            height = self.frame_height
            width = int(height * 9 / 16) + 1
            file.write("crop=%s:%s:0:0,\n" % (width, height))
            title = self.title
            subtitle = self.subtitle
            youtube_channel = self.youtube_channel
            if title:
                file.write(
                    f"drawtext=fontfile=./AGENCYB.ttf:text='{title}':fontcolor=white:fontsize=(h/35):x=({width}-text_w)/2:y=({height}-text_h-{height}/30),\n")
            if subtitle:
                file.write(
                    f"drawtext=fontfile=./AGENCYB.ttf:text='{subtitle}':fontcolor=white:fontsize=(h/55):x=({width}-text_w)/2:y=({height}+15-{height}/30),\n"
                )
            if youtube_channel:
                file.write(
                    f"drawtext=fontfile=./AGENCYB.ttf:text='{youtube_channel}':fontcolor=white:fontsize=(h/55):x=({width}-text_w)/2:y=({height}/30)\n")

    def write_to_file_dry(self):
        with open(self.output, "w") as file:
            title = self.title
            subtitle = self.subtitle
            youtube_channel = self.youtube_channel
            width = self.frame_width
            height = self.frame_height
            file.write(
                f"drawtext=fontfile=./AGENCYB.ttf:text='{title}':fontcolor=white:fontsize=(h/35):x=({width}-text_w)/2:y=({height}-text_h-{height}/30)\n,")
            file.write(
                f"drawtext=fontfile=./AGENCYB.ttf:text='{subtitle}':fontcolor=white:fontsize=(h/55):x=({width}-text_w)/2:y=({height}-{height}/30),\n"
            )
            file.write(
                f"drawtext=fontfile=./AGENCYB.ttf:text='{youtube_channel}':fontcolor=white:fontsize=(h/55):x=({width}-text_w)/2:y=({height}/30)\n")


def main():
    arguments = ProgramArguments()
    # check if the file exists
    if not os.path.exists(arguments.file):
        print(f"File {arguments.file} does not exist")
        return
    vs = cv2.VideoCapture(arguments.file)
    frame_0 = vs.read()[1]
    frame_height, frame_width = frame_0.shape[:2]
    Rectangle.final_width = frame_height / 16 * 9
    Rectangle.final_height = frame_height
    app = App(arguments, frame_width, frame_height)
    if app.dry_run:
        print("DRY RUN...")
        app.write_to_file_dry()
        return

    rectangles = app.collect_rectangles(vs)
    centered_frames = app.run(rectangles)
    if app.debug:
        for centered_frame in centered_frames:
            for center in centered_frame.get_centers():
                if center is None:
                    print("None center")
                    continue
                print(center.get_frame_number(), center.get_x())
            print("----")
    vs.set(cv2.CAP_PROP_POS_FRAMES, 0)
    vs.release()
    cv2.destroyAllWindows()
    steps = app.retrieve_steps(centered_frames)
    result = []
    for scene_steps in steps:
        result.extend(app.smooth_steps(scene_steps))
    app.write(result)


if __name__ == "__main__":
    main()
