#!/usr/bin/env python
__author__ = 'solivr'

import numpy as np
import tensorflow as tf
import warpctc_tensorflow
from tensorflow.contrib.rnn import BasicLSTMCell

from .decoding import get_words_from_chars


def weightVar(shape, mean=0.0, stddev=0.02, name='weights'):
    initW = tf.truncated_normal(shape=shape, mean=mean, stddev=stddev)
    return tf.Variable(initW, name=name)


def biasVar(shape, value=0.0, name='bias'):
    initb = tf.constant(value=value, shape=shape)
    return tf.Variable(initb, name=name)


def conv2d(input, filter, strides=[1, 1, 1, 1], padding='SAME', name=None):
    return tf.nn.conv2d(input, filter, strides=strides, padding=padding, name=name)


def deep_cnn(inputImgs: tf.Tensor, isTraining: bool) -> tf.Tensor:
    input_tensor = inputImgs
    if input_tensor.shape[-1] == 1:
        input_channels = 1
    if input_tensor.shape[-1] == 3:
        input_channels = 3

    # Following source code, not paper

    with tf.variable_scope('deep_cnn'):
        # - conv1 - maxPool2x2
        with tf.variable_scope('layer1'):
            W = weightVar([3, 3, input_channels, 64])
            b = biasVar([64])
            conv = conv2d(input_tensor, W, name='conv')
            out = tf.nn.bias_add(conv, b)
            conv1 = tf.nn.relu(out)
            pool1 = tf.nn.max_pool(conv1, [1, 2, 2, 1], strides=[1, 2, 2, 1],
                                   padding='SAME', name='pool')

            # tf.summary.image('1st_sample', pool1[:, :, :, :1], 1)
            weights = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer1/weights:0'][0]
            tf.summary.histogram('weights', weights)
            bias = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer1/bias:0'][0]
            tf.summary.histogram('bias', bias)

        # - conv2 - maxPool 2x2
        with tf.variable_scope('layer2'):
            W = weightVar([3, 3, 64, 128])
            b = biasVar([128])
            conv = conv2d(pool1, W)
            out = tf.nn.bias_add(conv, b)
            conv2 = tf.nn.relu(out)
            pool2 = tf.nn.max_pool(conv2, [1, 2, 2, 1], strides=[1, 2, 2, 1],
                                   padding='SAME', name='pool1')

            # tf.summary.image('1st_sample', pool2[:, :, :, :1], 1)
            weights = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer2/weights:0'][0]
            tf.summary.histogram('weights', weights)
            bias = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer2/bias:0'][0]
            tf.summary.histogram('bias', bias)

        # - conv3 - w/batch-norm (as source code, not paper)
        with tf.variable_scope('layer3'):
            W = weightVar([3, 3, 128, 256])
            b = biasVar([256])
            conv = conv2d(pool2, W)
            out = tf.nn.bias_add(conv, b)
            b_norm = tf.layers.batch_normalization(out, axis=-1,
                                                   training=isTraining, name='batch-norm')
            conv3 = tf.nn.relu(b_norm, name='ReLU')

            weights = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer3/weights:0'][0]
            tf.summary.histogram('weights', weights)
            bias = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer3/bias:0'][0]
            tf.summary.histogram('bias', bias)

        # - conv4 - maxPool 2x1
        with tf.variable_scope('layer4'):
            W = weightVar([3, 3, 256, 256])
            b = biasVar([256])
            conv = conv2d(conv3, W)
            out = tf.nn.bias_add(conv, b)
            conv4 = tf.nn.relu(out)
            pool4 = tf.nn.max_pool(conv4, [1, 2, 2, 1], strides=[1, 2, 1, 1],
                                   padding='SAME', name='pool4')

            # tf.summary.image('1st_sample', pool4[:, :, :, :1], 1)
            weights = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer4/weights:0'][0]
            tf.summary.histogram('weights', weights)
            bias = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer4/bias:0'][0]
            tf.summary.histogram('bias', bias)

        # - conv5 - w/batch-norm
        with tf.variable_scope('layer5'):
            W = weightVar([3, 3, 256, 512])
            b = biasVar([512])
            conv = conv2d(pool4, W)
            out = tf.nn.bias_add(conv, b)
            b_norm = tf.layers.batch_normalization(out, axis=-1,
                                                   training=isTraining, name='batch-norm')
            conv5 = tf.nn.relu(b_norm)

            weights = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer5/weights:0'][0]
            tf.summary.histogram('weights', weights)
            bias = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer5/bias:0'][0]
            tf.summary.histogram('bias', bias)

        # - conv6 - maxPool 2x1 (as source code, not paper)
        with tf.variable_scope('layer6'):
            W = weightVar([3, 3, 512, 512])
            b = biasVar([512])
            conv = conv2d(conv5, W)
            out = tf.nn.bias_add(conv, b)
            conv6 = tf.nn.relu(out)
            pool6 = tf.nn.max_pool(conv6, [1, 2, 2, 1], strides=[1, 2, 1, 1],
                                   padding='SAME', name='pool6')

            weights = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer6/weights:0'][0]
            tf.summary.histogram('weights', weights)
            bias = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer6/bias:0'][0]
            tf.summary.histogram('bias', bias)

        # - conv 7 - w/batch-norm (as source code, not paper)
        with tf.variable_scope('layer7'):
            W = weightVar([2, 2, 512, 512])
            b = biasVar([512])
            conv = conv2d(pool6, W, padding='VALID')
            out = tf.nn.bias_add(conv, b)
            b_norm = tf.layers.batch_normalization(out, axis=-1,
                                                   training=isTraining, name='batch-norm')
            conv7 = tf.nn.relu(b_norm)

            weights = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer7/weights:0'][0]
            tf.summary.histogram('weights', weights)
            bias = [var for var in tf.global_variables() if var.name == 'deep_cnn/layer7/bias:0'][0]
            tf.summary.histogram('bias', bias)

        cnn_net = conv7

        with tf.variable_scope('Reshaping_cnn'):
            shape = cnn_net.get_shape().as_list()  # [batch, height, width, features]
            transposed = tf.transpose(cnn_net, perm=[0, 2, 1, 3],
                                      name='transposed')  # [batch, width, height, features]
            conv_reshaped = tf.reshape(transposed, [-1, shape[2], shape[1] * shape[3]],
                                       name='reshaped')  # [batch, width, height x features]

    return conv_reshaped


def deep_bidirectional_lstm(inputs: tf.Tensor, params: dict) -> tf.Tensor:
    # Prepare data shape to match `bidirectional_rnn` function requirements
    # Current data input shape: (batch_size, n_steps, n_input) "(batch, time, height)"

    listNHidden = [256, 256]
    nClasses = 37

    with tf.name_scope('deep_bidirectional_lstm'):
        # Forward direction cells
        fw_cell_list = [BasicLSTMCell(nh, forget_bias=1.0) for nh in listNHidden]
        # Backward direction cells
        bw_cell_list = [BasicLSTMCell(nh, forget_bias=1.0) for nh in listNHidden]

        lstm_net, _, _ = tf.contrib.rnn.stack_bidirectional_dynamic_rnn(fw_cell_list,
                                                                        bw_cell_list,
                                                                        inputs,
                                                                        dtype=tf.float32
                                                                        )

        # Dropout layer
        lstm_net = tf.nn.dropout(lstm_net, keep_prob=params['keep_prob'])

        with tf.variable_scope('Reshaping_rnn'):
            shape = lstm_net.get_shape().as_list()  # [batch, width, 2*n_hidden]
            rnn_reshaped = tf.reshape(lstm_net, [-1, shape[-1]])  # [batch x width, 2*n_hidden]

        with tf.variable_scope('fully_connected'):
            W = weightVar([listNHidden[-1]*2, nClasses])
            b = biasVar([nClasses])
            fc_out = tf.nn.bias_add(tf.matmul(rnn_reshaped, W), b)

            # Summaries
            weights = [var for var in tf.global_variables()
                       if var.name == 'deep_bidirectional_lstm/fully_connected/weights:0'][0]
            tf.summary.histogram('weights', weights)
            bias = [var for var in tf.global_variables()
                    if var.name == 'deep_bidirectional_lstm/fully_connected/bias:0'][0]
            tf.summary.histogram('bias', bias)

        lstm_out = tf.reshape(fc_out, [-1, shape[1], nClasses], name='reshape_out')  # [batch, width, n_classes]

        rawPred = tf.argmax(tf.nn.softmax(lstm_out), axis=2, name='raw_prediction')

        # Swap batch and time axis
        lstm_out = tf.transpose(lstm_out, [1, 0, 2], name='transpose_time_major')  # [width(time), batch, n_classes]

        return lstm_out, rawPred


def crnn_fn(features, labels, mode, params):
    """
    :param features: dict {
                            'images'
                            'rnn_seq_length'
                            'target_seq_length' }
    :param labels: labels. flattend (1D) array with encoded label (one code per character)
    :param mode:
    :param params: dict {
                            'input_shape'
                            'keep_prob'
                            'starting_learning_rate'
                            'optimizer'
                            'decay_steps'
                            'decay_rate'
                            'max_length'
                            'digits_only'  (for predicting digits only)
                        }
    :return:
    """

    if mode == 'train':
        isTraining = True
        params['keep_prob'] = 0.7
    else:
        isTraining = False
        params['keep_prob'] = 1.0

    # Initialization
    eval_metric_ops = dict()
    loss_ctc = None
    train_op = None

    # tf.summary.image('input_image', features['images'], 3)

    conv = deep_cnn(features['images'], isTraining)
    logprob, raw_pred = deep_bidirectional_lstm(conv, params=params)  # params: rnn_seq_length, keep_prob

    # Compute seq_len from image width
    n_pools = 2 * 2  # 2x2 pooling in dimension W on layer 1 and 2
    seq_len_inputs = tf.divide(features['images_widths'], n_pools, name='seq_len_input_op') - 1

    if params['digits_only']:
        # Create array to substract
        n_chars = 37
        n_digits = 10
        mask = n_digits*[0] + (n_chars - n_digits - 1)*[100] + [0]
        logprob = logprob - tf.constant(mask, dtype=tf.float32)

    predictions_dict = {'prob': logprob, 'raw_predictions': raw_pred}

    blank_label_code = 36
    if not mode == tf.estimator.ModeKeys.PREDICT:
        # Alphabet and codes
        alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-'
        keys = [c for c in alphabet]
        values = list(range(blank_label_code)) + list(range(10, blank_label_code + 1))

        # Convert string to code
        with tf.name_scope('str2code_conversion'):
            table_str2int = tf.contrib.lookup.HashTable(tf.contrib.lookup.KeyValueTensorInitializer(keys, values), -1)
            splited = tf.string_split(labels, delimiter='')
            codes = table_str2int.lookup(splited.values)
            sparse_code_target = tf.SparseTensor(splited.indices, codes, splited.dense_shape)

        seq_lengths_labels = tf.segment_max(sparse_code_target.indices[:, 1], sparse_code_target.indices[:, 0]) + 1

        # Loss
        loss_ctc = warpctc_tensorflow.ctc(activations=predictions_dict['prob'],
                                          flat_labels=sparse_code_target.values,
                                          label_lengths=tf.cast(seq_lengths_labels, tf.int32),
                                          input_lengths=tf.cast(seq_len_inputs, dtype=tf.int32),
                                          blank_label=blank_label_code)
        loss_ctc = tf.reduce_mean(loss_ctc)

        # loss_ctc = tf.nn.ctc_loss(labels=sparse_code_target,
        #                           inputs=predictions_dict['prob'],
        #                           sequence_length=tf.cast(sequence_lengths, tf.int32),
        #                           preprocess_collapse_repeated=False,
        #                           ctc_merge_repeated=True,
        #                           ignore_longer_outputs_than_inputs=False,
        #                           time_major=True)
        # loss_ctc = tf.reduce_mean(loss_ctc)

        # Create an ExponentialMovingAverage object
        ema = tf.train.ExponentialMovingAverage(decay=0.99)
        # Create the shadow variables, and add ops to maintain moving averages
        maintain_averages_op = ema.apply([loss_ctc])
        loss_ema = ema.average(loss_ctc)

        # Train op
        global_step = tf.train.get_or_create_global_step()
        learning_rate = tf.train.exponential_decay(params['starting_learning_rate'], global_step, params['decay_steps'],
                                                   params['decay_rate'], staircase=True)

        tf.summary.scalar('learning_rate', learning_rate)
        tf.summary.scalar('ema_loss', loss_ema)

        if params['optimizer'] == 'ada':
            optimizer = tf.train.AdadeltaOptimizer(learning_rate)
        elif params['optimizer'] == 'adam':
            optimizer = tf.train.AdamOptimizer(learning_rate, beta1=0.5)
        elif params['optimizer'] == 'rms':
            optimizer = tf.train.RMSPropOptimizer(learning_rate)
        else:
            print('Error, no optimizer. RMS by default.')
            optimizer = tf.train.RMSPropOptimizer(learning_rate)

        update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
        with tf.control_dependencies(update_ops + [maintain_averages_op]):
            train_op = optimizer.minimize(loss_ctc, global_step=global_step)

    # Evaluation ops
    if not mode == tf.estimator.ModeKeys.TRAIN:
        # Convert code labels to string labels
        with tf.name_scope('code2str_conversion'):
            keys = np.arange(blank_label_code + 1, dtype=np.int64)
            alphabet_short = '0123456789abcdefghijklmnopqrstuvwxyz-'
            values = [c for c in alphabet_short]
            table_int2str = tf.contrib.lookup.HashTable(tf.contrib.lookup.KeyValueTensorInitializer(keys, values), '?')

            sparse_code_pred, log_probability = tf.nn.ctc_beam_search_decoder(predictions_dict['prob'],
                                                                              sequence_length=tf.cast(seq_len_inputs, tf.int32),
                                                                              merge_repeated=False,  # already merged in ctc_loss
                                                                              beam_width=100,
                                                                              top_paths=2)
        sparse_code_pred = sparse_code_pred[0]
        # Find a way to estimate the confidence in the prediction
        predictions_dict['difference_logprob'] = tf.subtract(log_probability[:, 0], log_probability[:, 1])
        # around 10.0 -> seems pretty sure, less than 5.0 bit unsure, some errors/challenging images

        sequence_lengths = tf.segment_max(sparse_code_pred.indices[:, 1], sparse_code_pred.indices[:, 0]) + 1

        pred_chars = table_int2str.lookup(sparse_code_pred)
        predictions_dict['words'] = get_words_from_chars(pred_chars.values, sequence_lengths=sequence_lengths)
        predictions_dict['filenames'] = features['filenames']

        if mode == tf.estimator.ModeKeys.EVAL:
            with tf.name_scope('evaluation'):
                CER = tf.metrics.mean(tf.edit_distance(sparse_code_pred, tf.cast(sparse_code_target, dtype=tf.int64)))
                accuracy = tf.metrics.accuracy(labels, predictions_dict['words'])

                eval_metric_ops = {
                                   'accuracy': accuracy,
                                   'CER': CER,
                                   }

    return tf.estimator.EstimatorSpec(
        mode=mode,
        predictions=predictions_dict,
        loss=loss_ctc,
        train_op=train_op,
        eval_metric_ops=eval_metric_ops,
        # scaffold=tf.train.Scaffold(init_fn=None)  # Specify init_fn to restore from previous model
    )