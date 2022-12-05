from harvesters.core import Harvester
import cv2

# enzatex camera interface
# requires
#  - camera driver (e.g. commom vision blox)
#  - https://github.com/genicam/harvesters
#  - opencv

CTI = r"C:\Program Files\STEMMER IMAGING\Common Vision Blox\GenICam\bin\win64_x64\TLIs\GEVTL.cti"
EXPOSURE_TIME = 49000
GAIN = 10


class Camera:
    def __init__(self):
        self._harvester = Harvester()
        self._harvester.add_file(CTI)
        self._harvester.update()
        self._acquirer = self._harvester.create()
        self._acquirer.num_buffers = 3
        params = self._acquirer.remote_device.node_map
        #params.ExposureTime.value = EXPOSURE_TIME
        #params.Gain.value = GAIN
        self._acquirer.start()
        
    def capture(self):
        '''retrieve next camera frame from the queue
        returns a HxWx3 numpy array (BGR image)
        '''
        for i in range(3):
            with self._acquirer.fetch() as buffer:
                component = buffer.payload.components[0]
                raw = component.data.reshape(component.height,component.width)
                bgr = cv2.cvtColor(raw, cv2.COLOR_BayerRGGB2BGR)
        return bgr
    
    def destroy(self):
        self._acquirer.stop()
        self._acquirer.destroy()
        self._harvester.reset()     
    
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