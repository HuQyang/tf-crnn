#!/usr/bin/env python
__author__ = 'solivr'

import os
import sys
import numpy as np
import cv2


def format_mjsynth_txtfile(path, file_split):
    with open(os.path.join(path, file_split), 'r') as f:
        lines = f.readlines()
    with open(os.path.join(path, 'lexicon.txt'), 'r') as f:
        lexicon = f.readlines()

    # Split lines into path and label
    linesplit = [l[:-1].split(' ') for l in lines]

    label_index = [int(s[1]) for s in linesplit]
    img_paths = [s[0] for s in linesplit]

    labels_string = [lexicon[ind][:-1] for ind in label_index]

    return img_paths, labels_string
# -------------------------------------------------


def ascii2label(ascii):
    """
    Offsets the ASCII code to have continuous labelling
    :param ascii: ascii code (int)
    :return: offset label (int)
    """
    n_digits = 10
    if 48 <= ascii <= 57:  # 0-9
        c = ascii - 48
    elif 65 <= ascii <= 90:  # A-Z
        c = ascii - 65 + n_digits
    elif 97 <= ascii <= 122:  # a-z
        c = ascii - 97 + n_digits
    return c
# -------------------------------------------------


def str2int_labels(labels_list):

    assert type(labels_list) is list

    n_labels = len(labels_list)
    maxLength = 0
    indices = []
    values = []
    seqLengths = []

    for i in range(n_labels):
        length_word = len(labels_list[i])
        if length_word > maxLength:
            maxLength = length_word

        for j in range(length_word):
            indices.append([i, j])
            values.append(ascii2label(ord(labels_list[i][j])))
        seqLengths.append(length_word)

    dense_shape = [n_labels, maxLength]
    indices = np.asarray(indices, dtype=np.int32)
    values = np.asarray(values, dtype=np.int32)
    dense_shape = np.asarray(dense_shape, dtype=np.int32)

    # return Sparse Tensor
    return (indices, values, dense_shape), seqLengths
# -------------------------------------------------


class Dataset:
    def __init__(self, config, path, mode):
        self.imgH = config.imgH
        self.imgW = config.imgW
        self.imgC = config.imgC
        self.datapath = path
        self.mode = mode  # test, train, val
        self.cursor = 0
        self.reset = False
        self.img_paths_list, self.labels_string_list = format_mjsynth_txtfile(self.datapath, 'annotation_{}.txt'.format(self.mode))
        self.nSamples = len(self.img_paths_list)

    def nextBatch(self, batch_size):
        """

        :param batch_size:
        :return: image batch,
                 label_set : tuple (sparse tensor, list string labels)
                 seqLength : length of the sequence
        """
        try:
            paths_batch_list = self.img_paths_list[self.cursor:self.cursor+batch_size]
            labels_batch_list = self.labels_string_list[self.cursor:self.cursor+batch_size]
        except IndexError:
            paths_batch_list = self.img_paths_list[self.cursor:-1]
            labels_batch_list = self.labels_string_list[self.cursor:-1]
            self.reset = True

        # Format labels to have a code per letter
        labels_1d, seqLengths = str2int_labels(labels_batch_list)
        label_set = (labels_1d, labels_batch_list)

        # Open and preprocess images
        images = list()
        for p in paths_batch_list:
            img_path = os.path.abspath(os.path.join(self.datapath, p))
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            try:
                resized = cv2.resize(img, (self.imgW, self.imgH), interpolation=cv2.INTER_CUBIC)
                images.append(resized)
            except:
                sys.exit('Error with image reading, {}. Aborted.'.format(p))

        images = np.asarray(images)
        self.cursor += batch_size

        if self.reset:
            self.cursor = 0
            self.reset = False

        return images, label_set, seqLengths