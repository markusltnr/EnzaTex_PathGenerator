# from OpenCV Tutorial
# https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html
import numpy as np
import cv2 as cv
import glob
import csv
import yaml


if __name__ == '__main__':
    # termination criteria
    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    # read in object points from file, first object point is on top left of
    # the image, second point right neighbor in top row, last point bottom
    # right
    objp = []
    with open('checkerboard_points.csv', newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',')
        for row in spamreader:
            objp.append([float(row[0]), float(row[1]), float(row[2])])
    objp = np.asarray(objp, dtype=np.float32)
    # Arrays to store object points and image points from all the images.
    objpoints = []  # 3d point in real world space
    imgpoints = []  # 2d points in image plane.
    images = glob.glob('EnzaTex/111*.bmp')
    images = sorted(images)
    for fname in images:
        img = cv.imread(fname)
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        # Find the chess board corners
        ret, corners = cv.findChessboardCornersSB(gray, (7, 7))
        # If found, add object points, image points (after refining them)
        if ret == True:
            objpoints.append(objp)
            imgpoints.append(corners)

    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(
        objpoints, imgpoints, gray.shape[::-1], None, None)

    data = {'camera_matrix': np.asarray(mtx).tolist(),
            'dist_coeff': np.asarray(dist).tolist(),
            'rotation_vector': np.asarray(rvecs[0]).tolist(),
            'translation_vector': np.asarray(tvecs[0]).tolist()}

    # save calibration matrix to a file
    with open("calibration_matrix.yaml", "w") as f:
        yaml.dump(data, f)
    
    rot, _ = cv.Rodrigues(rvecs[0])
    
    mean_error = 0
    for i in range(len(objpoints)):
        imgpoints2, _ = cv.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
        error = cv.norm(imgpoints[i], imgpoints2, cv.NORM_L2)/len(imgpoints2)
        mean_error += error
        print(error)
    print( "total error: {}".format(mean_error/len(objpoints)) )
 