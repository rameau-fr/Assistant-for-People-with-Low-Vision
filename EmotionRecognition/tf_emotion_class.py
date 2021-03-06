from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import argparse
import sys
import cv2
import tensorflow as tf
#from dataset_loader import DatasetLoader
import numpy as np
from math import floor

import pdb

DATA_PATH = "path to your dataset"
MODEL_PATH = "path to your model" 

class EmotionPredictor:
	"""docstring for EmotionPredictor"""
	def __init__(self):
		self.model_path = MODEL_PATH
		with tf.device('/gpu:0'):
			self.x = tf.placeholder(tf.float32, [None, 48, 48, 1])
			self.keep_prob = tf.placeholder(tf.float32)

			x_image = tf.reshape(self.x, [-1, 48, 48, 1])


			### first conv block ###
			W_conv1 = self.weight_variable([5,5,1,64])
			b_conv1 = self.bias_variable([64])
			h_conv1 = tf.nn.relu(self.conv2d(x_image,W_conv1)+b_conv1)
			h_pool1 = self.max_pool_2x2(h_conv1)

			### second conv block ###
			W_conv2 = self.weight_variable([5, 5, 64, 64])
			b_conv2 = self.bias_variable([64])
			h_conv2 = tf.nn.relu(self.conv2d(h_pool1, W_conv2) + b_conv2)
			hdrop2 = tf.nn.dropout(h_conv2, self.keep_prob)
			h_pool2 = self.max_pool_2x2(hdrop2)

			### third conv block ###
			W_conv3 = self.weight_variable([4, 4, 64, 128])
			b_conv3 = self.bias_variable([128])
			h_conv3 = tf.nn.relu(self.conv2d(h_pool2, W_conv3) + b_conv3)
			hdrop3 = tf.nn.dropout(h_conv3, self.keep_prob)
			hdrop3_flat = tf.reshape(hdrop3,[-1, 12 * 12 * 128]) #12 * 12 * 128

			### fully-connected layer 1 ###
			W_fc1 = self.weight_variable([12 * 12 * 128, 3072])
			b_fc1 = self.bias_variable([3072])
			h_fc1 = tf.nn.relu(tf.matmul(hdrop3_flat,W_fc1)+b_fc1)
			
			### fully-connected layer 2 ###
			W_fc2 = self.weight_variable([3072, 1024])
			b_fc2 = self.bias_variable([1024])
			h_fc2 = tf.nn.relu(tf.matmul(h_fc1,W_fc2)+b_fc2)

			### fully-connected layer 2 ###
			W_fc3 = self.weight_variable([1024, 7])
			b_fc3 = self.bias_variable([7])

			self.y_conv = tf.matmul(h_fc2,W_fc3)+b_fc3

			self.saver = tf.train.Saver()

		gpu_options = tf.GPUOptions(visible_device_list = '1', per_process_gpu_memory_fraction = 0.1, allow_growth = False)
		session_config = tf.ConfigProto(allow_soft_placement = True, log_device_placement = False, gpu_options = gpu_options)

		self.sess = tf.Session(config = session_config)

		ckpt = tf.train.get_checkpoint_state(self.model_path)
		if ckpt and tf.train.checkpoint_exists(ckpt.model_checkpoint_path):
			print("Reading model parameters from %s" % ckpt.model_checkpoint_path)
			self.saver.restore(self.sess, ckpt.model_checkpoint_path)

	def conv2d(self, x, W):
	  """conv2d returns a 2d convolution layer with full stride."""
	  return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')

	def max_pool_2x2(self, x):
	  """max_pool_2x2 downsamples a feature map by 2X."""
	  return tf.nn.max_pool(x, ksize=[1, 2, 2, 1],
	                        strides=[1, 2, 2, 1], padding='SAME')

	def weight_variable(self, shape):
	  """weight_variable generates a weight variable of a given shape."""
	  initial = tf.truncated_normal(shape, stddev=0.1)
	  return tf.Variable(initial)

	def bias_variable(self, shape):
	  """bias_variable generates a bias variable of a given shape."""
	  initial = tf.constant(0.1, shape=shape)
	  return tf.Variable(initial)

	def get_batch(self, X, y, batch_size = 100):
		indx = np.random.choice(X.shape[0],batch_size)
		X_batch = X[indx]
		y_batch = y[indx]
		return (X_batch, y_batch)

	def train_emotions(self):
		y_ = tf.placeholder(tf.float32, [None, 7])
		# dataset loading
		X_train = np.load(DATA_PATH + "training set").astype(np.float32)
		y_train = np.load(DATA_PATH + "training labels set").astype(np.float32)
		X_test = np.load(DATA_PATH + "validation set").astype(np.float32)
		y_test = np.load(DATA_PATH + "validation labels set").astype(np.float32)

		learning_rate = 0.0001
		cross_entropy = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(labels=y_, logits=self.y_conv))
		train_step = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cross_entropy)
		correct_prediction = tf.equal(tf.argmax(self.y_conv, 1), tf.argmax(y_, 1))
		accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

		saver = tf.train.Saver()

		batch_size = 2000

		with tf.Session() as sess:
			ckpt = tf.train.get_checkpoint_state(self.model_path)
			if ckpt and tf.train.checkpoint_exists(ckpt.model_checkpoint_path):
				print("Reading model parameters from %s" % ckpt.model_checkpoint_path)
				saver.restore(sess, ckpt.model_checkpoint_path)
			else:
				print("Created model with fresh parameters.")
				sess.run(tf.global_variables_initializer())

			for i in range(20000):
				batch = self.get_batch(self.X_train, self.y_train, batch_size = batch_size)

				_,loss_val = sess.run([train_step, cross_entropy],feed_dict={self.x: batch[0], y_: batch[1], self.keep_prob: 0.5})
				
				train_accuracy = accuracy.eval(feed_dict={ self.x: batch[0], y_: batch[1], self.keep_prob: 0.5})

				if (i % 10) == 0:
					print('step %d, loss=%f, training accuracy %g' % (i, loss_val, train_accuracy))
				
				if (i % 500) == 0:
					print('test accuracy %g' % accuracy.eval(feed_dict={self.x: self.X_test, y_: self.y_test, self.keep_prob: 1.0}))

	def format_image(self, image, face):
		if len(image.shape) > 2 and image.shape[2] == 3:
			image = cv2.cvtColor(image.astype(np.float32), cv2.COLOR_BGR2GRAY)
		else:
			image = cv2.imdecode(image.astype(np.float32), cv2.CV_LOAD_IMAGE_GRAYSCALE)
		# Chop image to face    
		image = image[face[1]:face[3], face[0]:face[2]]
		#Resize image to network size
		try:
			image = cv2.resize(image, (48, 48), interpolation = cv2.INTER_CUBIC) / 255.
		except Exception:
			print("[+] Problem during resize")
			return None
		return image

	def predict(self, img, face):
		processed_img = self.format_image(img, face).reshape([-1, 48, 48, 1])
		if img is not None:
			idx = self.sess.run(tf.argmax(tf.nn.softmax(self.y_conv),1), feed_dict = {self.x : processed_img, self.keep_prob: 1.0})
			if idx[0] == 0:
			  	return 'angry'
			elif idx[0] == 1:
			  	return 'disgusted'
			elif idx[0] == 2:
			  	return 'fearful'
			elif idx[0] == 3:
			  	return 'happy'
			elif idx[0] == 4:
			  	return 'sad'
			elif idx[0] == 5:
			  	return 'surprised'
			else:
			 	return 'neutral'
		else:
			return "[+] Faces are not found"

# unquote to test
#emotion = EmotionPredictor()
#emotion.predict()
#emotion.train_emotions()
