import cv2
import numpy as np


def path_generation(camera_dict, img_obj, img_bg,
                    bg_thresh=50, spacing=20, dilation=10):
    """generates path coordinates and visualization image

    Arguments:
        camera_dict {dict} -- camera parameters (matrix, dist coeff, tvecs, rvecs)
        img_obj {_type_} -- image with an object on the plate
        img_bg {_type_} -- image of only the background

    Keyword Arguments:
        bg_thresh {int} -- threshold for object masking (default: {50})
        spacing {int} -- space in mm (roughly) between two path rows (default: {20})
        dilation {int} -- space in mm (roughly) that is added at the edges of the maks (default: {10})

    Returns:
        path_img  {numpy array HxWx3, uint8} -- visualization image with path drawn
        world_coords {numpy array Nx2, float64} -- coordinates of the path points
    """
    img = img_obj
    img_mask = segment_mask_bg(img_bg, img_obj, bg_thresh)

    w, h = img.shape[0], img.shape[1]
    corners = np.asarray([[0., 0.], [w, 0], [0, h], [w, h]])
    corners_mm = pixel2world(corners, camera_dict, undistort=True)

    a = (corners_mm[0, 0] - corners_mm[1, 0]) / w
    b = (corners_mm[2, 0] - corners_mm[3, 0]) / w
    c = (corners_mm[2, 1] - corners_mm[0, 1]) / h
    d = (corners_mm[3, 1] - corners_mm[1, 1]) / h
    pixmm = np.mean([a, b, c, d])

    _, thresh = cv2.threshold(img_mask, 127, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(
        thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contour_img = np.zeros(img_mask.shape)
    cv2.drawContours(contour_img, contours, -1, (255, 0, 0),
                     int(2 * dilation / pixmm),)
    contour_img = np.array(contour_img, dtype=np.uint8)
    contour_points = np.zeros(contour_img.shape, dtype=np.uint8)
    skip_rows = int(spacing / pixmm)
    for row in range(0, w, skip_rows):
        for col in range(0, h, 1):
            if contour_img[row][col] > 0:
                contour_points[row][col] = 255
    # take only first and last point of every row
    for row in range(0, w, skip_rows):
        if np.sum(contour_points[row]) > 0:
            indices = np.where(contour_points[row] > 0)
            rm_indices = indices[0][1:-1]
            for i in rm_indices:
                contour_points[row][i] = 0

    indices = np.where(contour_points[:, :] != [0])
    coordinates = list(zip(indices[1], indices[0]))
    coordinates_sorted = []
    for i in range(0, len(coordinates) - 4, 4):
        coordinates_sorted.append(coordinates[i])
        coordinates_sorted.append(coordinates[i + 1])
        coordinates_sorted.append(coordinates[i + 3])
        coordinates_sorted.append(coordinates[i + 2])

    if len(coordinates) % 4 == 0:
        i = len(coordinates) - 1
        coordinates_sorted.append(coordinates[i - 3])
        coordinates_sorted.append(coordinates[i - 2])
        coordinates_sorted.append(coordinates[i])
        coordinates_sorted.append(coordinates[i - 1])
    elif len(coordinates) % 4 == 2:
        i = len(coordinates) - 1
        coordinates_sorted.append(coordinates[i - 1])
        coordinates_sorted.append(coordinates[i])

    for i in range(len(coordinates_sorted) - 1):
        cv2.line(contour_points,
                 coordinates_sorted[i],
                 coordinates_sorted[i + 1],
                 (255, 255, 255), 8)

    world_coords = pixel2world(np.asarray(coordinates), camera_dict)
    contour_points = cv2.cvtColor(contour_points, cv2.COLOR_GRAY2RGB)
    path_img = cv2.addWeighted(img, 0.7, contour_points, 0.3, 0)

    return path_img, world_coords


def pixel2world(points, camera_dict, undistort=True):
    """ take pixel coordinates and transform them into world coordinates
        with Z=0
    Arguments:
        points {numpy.array [n, 2]} -- n points consisting of u,v image coordinates
        camera_dict {dict} -- camera dictionary that contains
                            camera_matrix, dist_coeff, rotation_vector
                            and translation_vector

    Returns:
        numpy array [2,]-- X, Y world coordinates
    """
    # Undistort pixel coordinates first
    int_mtx = np.asarray(camera_dict["camera_matrix"])  # camera intrinsics
    dst = np.asarray(camera_dict["dist_coeff"])  # distortion coefficients
    rvec = np.asarray(camera_dict["rotation_vector"])
    tvec = np.asarray(camera_dict["translation_vector"])
    if undistort:
        undist = cv2.undistortPoints(points.astype(np.float32), int_mtx, dst)
        u_new = undist[:, :, 0] * int_mtx[0, 0] + int_mtx[0, 2]
        v_new = undist[:, :, 1] * int_mtx[1, 1] + int_mtx[1, 2]
        point_new = np.concatenate((u_new, v_new), axis=1)
    else:
        point_new = points
    # since Z in world coordinates is 0, remove third column from
    # transformation matrix
    rot, _ = cv2.Rodrigues(rvec)
    ext_mtx = np.concatenate((rot[:, :2], tvec), axis=1)
    tf_mtx = np.matmul(int_mtx, ext_mtx)
    # invert it
    inv_tf = np.linalg.inv(tf_mtx)
    # calculate world coordinates
    im_coord = np.concatenate(
        ((point_new), np.ones(
            (point_new.shape[0], 1))), axis=1)[
        :, :, np.newaxis]
    world_coord = np.matmul(inv_tf, im_coord).squeeze()
    world_coord = (world_coord / world_coord[:, 2, None])
    return world_coord[:, :2]


def segment_mask_bg(img_background, img_object, bg_thresh):
    w, h = img_background.shape[0], img_background.shape[1]
    brightness_mask = np.ones((w, h), np.uint8)

    cv2.rectangle(brightness_mask, (200, 200), (h - 200, w - 200), 0, -1)
    brightness_mask = brightness_mask.astype(bool)
    bg_mean = np.mean(img_background[brightness_mask], 0)
    obj_mean = np.mean(img_object[brightness_mask], 0)
    beta = bg_mean - obj_mean

    img_object[:, :, 0] = cv2.convertScaleAbs(
        img_object[:, :, 0], alpha=1., beta=beta[0])
    img_object[:, :, 1] = cv2.convertScaleAbs(
        img_object[:, :, 1], alpha=1., beta=beta[1])
    img_object[:, :, 2] = cv2.convertScaleAbs(
        img_object[:, :, 2], alpha=1., beta=beta[2])

    img_sub = cv2.absdiff(img_background, img_object)
    img_sub = cv2.GaussianBlur(img_sub, (15, 15), 6)
    img_sub = (
        (np.any(img_sub[:, :] > bg_thresh, axis=2)) * 255).astype(np.uint8)
    return img_sub


if __name__ == "__main__":
    import yaml

    # load calibration matrix
    with open("calibration_matrix.yaml", "r") as f:
        camera_dict = yaml.safe_load(f)
    # load background and object image
    img_bg = cv2.imread("background/2000.bmp")
    img_obj = cv2.imread("textiles/2001.bmp")
    print(img_obj.shape, img_bg.shape)
    # path generation
    img, coords = path_generation(
        camera_dict, img_obj, img_bg, bg_thresh=50, spacing=10, dilation=10)

    # show visualization image and coordinates
    cv2.namedWindow("EnzaTex", cv2.WINDOW_NORMAL)
    cv2.imshow("EnzaTex", img)
    cv2.resizeWindow("EnzaTex", 1000, 1000)
    print(coords)
    cv2.waitKey(0)
