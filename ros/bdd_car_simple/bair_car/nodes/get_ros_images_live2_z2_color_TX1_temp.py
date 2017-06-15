#!/usr/bin/env python
"""
reed to run roslaunch first, e.g.,

roslaunch bair_car bair_car.launch use_zed:=true record:=false
"""
try:

	########################################################
	#          CAFFE SETUP SECTION
	import caffe
	caffe.set_device(0)
	caffe.set_mode_gpu()
	from kzpy3.utils import *
	from kzpy3.teg1.rosbag_work.get_data_from_bag_files2 import *
	import cv2
	os.chdir(home_path) # this is for the sake of the train_val.prototxt
	import kzpy3.teg2.car_run_params
	from kzpy3.teg2.car_run_params import *

	#solver_file_path = opjh("kzpy3/caf5/z2_color/solver_live.prototxt")
	#weights_file_path = opjh('kzpy3/caf5/z2_color/z2_color.caffemodel') #
	def setup_solver():
		solver = caffe.SGDSolver(solver_file_path)
		for l in [(k, v.data.shape) for k, v in solver.net.blobs.items()]:
			print(l)
		for l in [(k, v[0].data.shape) for k, v in solver.net.params.items()]:
			print(l)
		return solver
	solver = setup_solver()
	if weights_file_path != None:
		print_stars(2)
		print "loading " + weights_file_path
		solver.net.copy_from(weights_file_path)
		print_stars(2)
	#
	########################################################


	########################################################
	#          ROSPY SETUP SECTION
	import roslib
	import std_msgs.msg
	import cv2
	from cv_bridge import CvBridge,CvBridgeError
	import rospy
	from sensor_msgs.msg import Image
	bridge = CvBridge()
	rospy.init_node('listener',anonymous=True)

	left_list = []
	right_list = []
	A = 0
	B = 0
	state = 0
	previous_state = 0
	state_transition_time_s = 0

	def state_callback(data):
		global state, previous_state
		if state != data.data:
			if state in [3,5,6,7] and previous_state in [3,5,6,7]:
				pass
			else:
				previous_state = state
		state = data.data
	def right_callback(data):
		global A,B, left_list, right_list, solver
		A += 1
		cimg = bridge.imgmsg_to_cv2(data,"bgr8")
		if len(right_list) > 5:
			right_list = right_list[-5:]
		right_list.append(cimg)
	def left_callback(data):
		global A,B, left_list, right_list
		B += 1
		cimg = bridge.imgmsg_to_cv2(data,"bgr8")
		if len(left_list) > 5:
			left_list = left_list[-5:]
		left_list.append(cimg)
	def state_transition_time_s_callback(data):
		global state_transition_time_s
		state_transition_time_s = data.data


	GPS2_lat = -999.99
	GPS2_long = -999.99
	GPS2_lat_orig = -999.99
	GPS2_long_orig = -999.99
	def GPS2_lat_callback(msg):
		global GPS2_lat
		GPS2_lat = msg.data
	def GPS2_long_callback(msg):
		global GPS2_long
		GPS2_long = msg.data

	camera_heading = 49.0
	def camera_heading_callback(msg):
		global camera_heading
		c = msg.data
		#print camera_heading
		if c > 90:
			c = 90
		if c < -90:
			c = -90
		c += 90
		c /= 180.
		
		c *= 99

		if c < 0:
			c = 0
		if c > 99:
			c = 99
		c = 99-c
		camera_heading = int(c)

	##
	########################################################

	import thread
	import time


	rospy.Subscriber("/bair_car/zed/right/image_rect_color",Image,right_callback,queue_size = 1)
	rospy.Subscriber("/bair_car/zed/left/image_rect_color",Image,left_callback,queue_size = 1)
	rospy.Subscriber('/bair_car/state', std_msgs.msg.Int32,state_callback)
	rospy.Subscriber('/bair_car/state_transition_time_s', std_msgs.msg.Int32, state_transition_time_s_callback)
	steer_cmd_pub = rospy.Publisher('cmd/steer', std_msgs.msg.Int32, queue_size=100)
	motor_cmd_pub = rospy.Publisher('cmd/motor', std_msgs.msg.Int32, queue_size=100)

	#rospy.Subscriber('/bair_car/GPS2_lat', std_msgs.msg.Float32, callback=GPS2_lat_callback)
	#rospy.Subscriber('/bair_car/GPS2_long', std_msgs.msg.Float32, callback=GPS2_long_callback)
	#rospy.Subscriber('/bair_car/GPS2_lat_orig', std_msgs.msg.Float32, callback=GPS2_lat_callback)
	#rospy.Subscriber('/bair_car/GPS2_long_orig', std_msgs.msg.Float32, callback=GPS2_long_callback)
	#rospy.Subscriber('/bair_car/camera_heading', std_msgs.msg.Float32, callback=camera_heading_callback)


	ctr = 0


	from kzpy3.teg2.global_run_params import *
	import kzpy3.teg2.car_run_params
	from kzpy3.teg2.car_run_params import *

	t0 = time.time()
	time_step = Timer(1)
	caffe_enter_timer = Timer(2)
	folder_display_timer = Timer(30)
	reload_timer = Timer(5)
	#verbose = False
	while not rospy.is_shutdown():
		if state in [3,5,6,7]:
			if (previous_state not in [3,5,6,7]):
				previous_state = state
				caffe_enter_timer.reset()
			if not caffe_enter_timer.check():
				#print caffe_enter_timer.check()
				print "waiting before entering caffe mode..."
				steer_cmd_pub.publish(std_msgs.msg.Int32(49))
				motor_cmd_pub.publish(std_msgs.msg.Int32(49))
				time.sleep(0.1)
				continue
			else:
				if len(left_list) > 4:
					l0 = left_list[-2]
					l1 = left_list[-1]
					r0 = right_list[-2]
					r1 = right_list[-1]

					solver.net.blobs['ZED_data'].data[0,0,:,:] = l0[:,:,0]
					solver.net.blobs['ZED_data'].data[0,1,:,:] = l1[:,:,0]
					solver.net.blobs['ZED_data'].data[0,2,:,:] = r0[:,:,0]
					solver.net.blobs['ZED_data'].data[0,3,:,:] = r1[:,:,0]
					solver.net.blobs['ZED_data'].data[0,4,:,:] = l0[:,:,1]
					solver.net.blobs['ZED_data'].data[0,5,:,:] = l1[:,:,1]
					solver.net.blobs['ZED_data'].data[0,6,:,:] = r0[:,:,1]
					solver.net.blobs['ZED_data'].data[0,7,:,:] = r1[:,:,1]
					solver.net.blobs['ZED_data'].data[0,8,:,:] = l0[:,:,2]
					solver.net.blobs['ZED_data'].data[0,9,:,:] = l1[:,:,2]
					solver.net.blobs['ZED_data'].data[0,10,:,:] = r0[:,:,2]
					solver.net.blobs['ZED_data'].data[0,11,:,:] = r1[:,:,2]
						

					solver.net.blobs['metadata'].data[0,0,:,:] = Racing#target_data[0]/99. #current steer
					solver.net.blobs['metadata'].data[0,1,:,:] = 0#target_data[len(target_data)/2]/99. #current motor
					solver.net.blobs['metadata'].data[0,2,:,:] = Follow
					solver.net.blobs['metadata'].data[0,3,:,:] = Direct
					solver.net.blobs['metadata'].data[0,4,:,:] = Play
					solver.net.blobs['metadata'].data[0,5,:,:] = Furtive
					

					solver.net.forward(start='ZED_data',end='ZED_data_pool2')

					solver.net.blobs['ZED_data_pool2'].data[:,:,:,:] /= 255.0
					solver.net.blobs['ZED_data_pool2'].data[:,:,:,:] -= 0.5

					solver.net.forward(start='conv1',end='ip2')

					caf_steer = 100*solver.net.blobs['ip2'].data[0,9]
					caf_motor = 100*solver.net.blobs['ip2'].data[0,19]

					"""
					if caf_motor > 60:
						caf_motor = (caf_motor-60)/39.0*10.0 + 60
					"""

					caf_motor = int((caf_motor-49.) * motor_gain + 49)
					caf_steer = int((caf_steer-49.) * steer_gain + 49)



					if caf_motor > 99:
						caf_motor = 99
					if caf_motor < 0:
						caf_motor = 0
					if caf_steer > 99:
						caf_steer = 99
					if caf_steer < 0:
						caf_steer = 0

					if verbose:
						print caf_motor,caf_steer,motor_gain,steer_gain,state
					
					if state in [3,6]:			
						steer_cmd_pub.publish(std_msgs.msg.Int32(caf_steer))
					if state in [6,7]:
						motor_cmd_pub.publish(std_msgs.msg.Int32(caf_motor))

		else:
			pass

		if state == 4 and state_transition_time_s > 30:
			print("Shutting down because in state 4 for 30+ s")
			unix('sudo shutdown -h now')
		if time_step.check():
			print(d2s("In state",state,"for",state_transition_time_s,"seconds, previous_state =",previous_state))
			time_step.reset()
			if not folder_display_timer.check():
				print("*** Data foldername = "+foldername+ '***')
		if reload_timer.check():
			reload(run_params)
			from run_params import *
			reload_timer.reset()

except Exception as e:
	print("********** Exception ***********************",'red')
	print(e.message, e.args)
	rospy.signal_shutdown(d2s(e.message,e.args))

