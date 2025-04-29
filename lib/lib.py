import cv2
import imutils
from cv2 import VideoCapture

from lib.model import Rectangle

OPENCV_OBJECT_TRACKERS = {
    "csrt": cv2.TrackerCSRT.create,
    "kcf": cv2.TrackerKCF.create,
    "mil": cv2.TrackerMIL.create,
}

LEFT_ARROW = 2424832
RIGHT_ARROW = 2555904


class RectangleTracker:

    def __init__(self, *, vs: VideoCapture, frame_width: int, gray: bool, file: str, ratio: float, tracker: str):
        self.gray = gray
        self.file = file
        self.ratio = ratio
        self.vs = vs
        self.frame_width = frame_width
        self.total_frames = int(vs.get(cv2.CAP_PROP_FRAME_COUNT))
        self.tracker = OPENCV_OBJECT_TRACKERS[tracker]()

    def track(self) -> {int: Rectangle}:
        rectangles: {int: Rectangle} = {}
        roi_found = False
        key = None
        cur_frame_number = 0
        total_frames = self.total_frames
        # put vs at the beginning
        self.vs.set(cv2.CAP_PROP_POS_FRAMES, 0)
        while cur_frame_number < self.total_frames:
            _, frame = self.vs.read()
            if frame is None:
                break
            resized_frame = imutils.resize(frame, width=int(self.frame_width / self.ratio))
            if self.gray:
                resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
            if cur_frame_number - 1 > 0 and rectangles.get(cur_frame_number - 1, None) is not None:
                # print previous rectangle
                rectangle = rectangles[cur_frame_number - 1]
                cv2.rectangle(resized_frame, rectangle.get_point1_unscaled(), rectangle.get_point2_unscaled(),
                              (150, 200, 150), 2)
                cv2.rectangle(resized_frame, rectangle.get_point1_final(), rectangle.get_point2_final(),
                              (0, 0, 255), 10)
                cv2.line(resized_frame, (rectangle.get_center_x(), 0),
                         (rectangle.get_center_x(), resized_frame.shape[0]),
                         (0, 0, 255), 2)
            if key == ord(" "):
                key = cv2.waitKeyEx(0)
                # if key left arrow or right arrow
                prev_rectangle = None
                if key == LEFT_ARROW and cur_frame_number > 0:
                    roi_found = False
                    while key in [LEFT_ARROW, RIGHT_ARROW] and cur_frame_number > 0:
                        if key == LEFT_ARROW:
                            cur_frame_number -= 1
                        elif key == RIGHT_ARROW:
                            cur_frame_number += 1
                            if cur_frame_number >= self.total_frames or cur_frame_number not in rectangles:
                                cur_frame_number -= 1
                                break
                        self.vs.set(cv2.CAP_PROP_POS_FRAMES, cur_frame_number)
                        resized_frame = imutils.resize(self.vs.read()[1], width=int(self.frame_width / self.ratio))
                        prev_rectangle = rectangles.get(cur_frame_number, None)
                        if prev_rectangle is not None:
                            cv2.rectangle(resized_frame, prev_rectangle.get_point1_unscaled(),
                                          prev_rectangle.get_point2_unscaled(),
                                          (180, 180, 180), 2)
                        cv2.putText(resized_frame, "Frame: {}/{}".format(cur_frame_number, total_frames), (10, 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.imshow(self.file, resized_frame)
                        key = cv2.waitKeyEx(0)
                if prev_rectangle is not None:
                    cv2.rectangle(resized_frame, prev_rectangle.get_point1_unscaled(),
                                  prev_rectangle.get_point2_unscaled(),
                                  (0, 0, 255), 2)

            if not roi_found:
                roi = cv2.selectROI(self.file, resized_frame, fromCenter=False, )
                rectangles[cur_frame_number] = Rectangle.from_roi(roi, cur_frame_number, self.ratio)
                while True:
                    try:
                        self.tracker.init(resized_frame, roi)
                        break
                    except:
                        roi = cv2.selectROI(self.file, resized_frame, fromCenter=False, )
                        rectangles[cur_frame_number] = Rectangle.from_roi(roi, cur_frame_number, self.ratio)
                roi_found = True
            else:
                cur_frame_number += 1
                (roi_found, box) = self.tracker.update(resized_frame)
                if roi_found:
                    (x, y, w, h) = [int(v) for v in box]
                    cv2.rectangle(resized_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    rectangles[cur_frame_number] = Rectangle(x, x + w, y, y + h, cur_frame_number, self.ratio)
            # add text
            cv2.putText(resized_frame, "Frame: {}".format(cur_frame_number), (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow(self.file, resized_frame)
            key = cv2.waitKey(1) & 0xFF
        return rectangles

def ffmpeg_line(center_x, center_y, start, end, frame_width, frame_height, width, height):
    center_x = int(center_x)
    center_y = int(center_y)
    frame_width = int(frame_width)
    frame_height = int(frame_height)
    x2 = int(center_x - width / 2)
    y2 = int(center_y - height / 2)
    if y2 < 0:
        y2 = 0
    if y2 + height > frame_height:
        y2 = frame_height - height
    if x2 <= 0:
        x2 = int(width / 2)
    if x2 < width:
        output = ""
        i = 0
        last = 0
        while (i + 1) * x2 <= width + x2:
            output += "swaprect=%s:%s:%s:0:%s:%s:enable='between(n,%s,%s)',\n" % (
                x2, height, i * x2, (i + 1) * x2, y2, start, end)
            last = i * x2
            i += 1
        rest = width - last
        output += "swaprect=%s:%s:%s:0:%s:%s:enable='between(n,%s,%s)',\n" % (
            rest, height, i * x2, i * x2 + rest, y2, start, end)

        return output
    elif x2 + width > frame_width:
        x2 = frame_width - width
    return "swaprect=%s:%s:0:0:%s:%s:enable='between(n,%s,%s)',\n" % (width, height, x2, y2, start, end)
