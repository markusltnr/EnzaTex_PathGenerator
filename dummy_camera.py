import cv2

class Camera:
    def __init__(self):
        self.vid = cv2.VideoCapture(0)
        
    def capture(self):
        '''retrieve next camera frame from the queue
        returns a HxWx3 numpy array (BGR image)
        '''
        for i in range(5):
            ret, bgr = self.vid.read()
        bgr = cv2.resize(bgr, (2448, 2048))
        
        return bgr
    
    def destroy(self):
        self.vid.release()
    
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.destroy()


if __name__ == "__main__":
    with Camera() as camera:
        while True:
            img = camera.capture()
            cv2.imshow('img',img)
            if cv2.waitKey(1)!=-1:
                break