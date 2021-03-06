#!/usr/bin/env python
"""
reed to run roslaunch first, e.g.,

roslaunch bair_car bair_car.launch use_zed:=true record:=false
"""
import sys, traceback
try:
    ########################################################
    #          KARAS SETUP SECTION
    from model_car.model.predict import get_trained_model, forward_pass
    from model_car.utils import *
    from model_car.data_analysis.data_parsing.get_data_from_bag_files import *
    import cv2
    os.chdir(home_path) # this is for the sake of the train_val.prototxt
    import model_car.car_run_params
    from model_car.car_run_params import *
    version = 'version_1b'
    #version = 'squeeze_net'
    #weights_file_path = opjh('model_car/model_car/model/z2_color_tf.npy') #
    weights_file_path = opjh('model_car/model_car/model/z2_color_version_1b_final.hdf5') #
    #weights_file_path = opjh('model_car/model_car/model/z2_color_squeeze_net_final.hdf5') #
    def setup_solver(weights_file_path):
        if weights_file_path != None:
            print "loading " + weights_file_path
        solver = get_trained_model(version, weights_file_path)
        return solver
    solver = setup_solver(weights_file_path)
    solver.summary()
    #
    ########################################################


    ########################################################
    #          ROSPY SETUP SECTION
    import roslib
    import std_msgs.msg
    import geometry_msgs.msg
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

    freeze = False
    def gyro_callback(msg):
        global freeze
        gyro = msg
        #if np.abs(gyro.y) > gyro_freeze_threshold:
        #    freeze = True
        if np.sqrt(gyro.y**2+gyro.z**2) > gyro_freeze_threshold:
            freeze = True
    def acc_callback(msg):
        global freeze
        acc = msg
        if np.abs(acc.z) > acc_freeze_threshold_z:
            freeze = True
        if acc.y < acc_freeze_threshold_z_neg:
            freeze = True
        if np.abs(acc.x) > acc_freeze_threshold_x:
            freeze = True
        #if np.abs(acc.y) > acc_freeze_threshold_y:
        #    freeze = True

    encoder_list = []
    def encoder_callback(msg):
        global encoder_list
        encoder_list.append(msg.data)
        if len(encoder_list) > 30:
            encoder_list = encoder_list[-30:]

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
    freeze_cmd_pub = rospy.Publisher('cmd/freeze', std_msgs.msg.Int32, queue_size=100)
    model_name_pub = rospy.Publisher('/bair_car/model_name', std_msgs.msg.String, queue_size=10)
    #rospy.Subscriber('/bair_car/GPS2_lat', std_msgs.msg.Float32, callback=GPS2_lat_callback)
    #rospy.Subscriber('/bair_car/GPS2_long', std_msgs.msg.Float32, callback=GPS2_long_callback)
    #rospy.Subscriber('/bair_car/GPS2_lat_orig', std_msgs.msg.Float32, callback=GPS2_lat_callback)
    #rospy.Subscriber('/bair_car/GPS2_long_orig', std_msgs.msg.Float32, callback=GPS2_long_callback)
    #rospy.Subscriber('/bair_car/camera_heading', std_msgs.msg.Float32, callback=camera_heading_callback)
    rospy.Subscriber('/bair_car/gyro', geometry_msgs.msg.Vector3, callback=gyro_callback)
    rospy.Subscriber('/bair_car/acc', geometry_msgs.msg.Vector3, callback=acc_callback)
    rospy.Subscriber('encoder', std_msgs.msg.Float32, callback=encoder_callback)

    ctr = 0


    #from kzpy3.teg2.global_run_params import *

    t0 = time.time()
    time_step = Timer(1)
    AI_enter_timer = Timer(2)
    folder_display_timer = Timer(30)
    git_pull_timer = Timer(60)
    reload_timer = Timer(10)
    AI_steer_previous = 49
    AI_motor_previous = 49
    #verbose = False
    
    
    while not rospy.is_shutdown():
        #state = 3 
        if state in [3,5,6,7]:
            
            if (previous_state not in [3,5,6,7]):
                previous_state = state
                AI_enter_timer.reset()
            if use_AI:
                if not AI_enter_timer.check():
                    #print AI_enter_timer.check()
                    print "waiting before entering AI mode..."
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
                        
                        ZED_data = {'ZED_data_left_frame1': l0, 'ZED_data_left_frame2': l1, 'ZED_data_right_frame1': r0, 'ZED_data_right_frame2': r1}
                        meta_data_label = {'Direct': Direct, 'Follow': Follow, 'Play': Play, 'Furtive': Furtive, 'AI': AI, 'Racing': Racing}
                        
                        [AI_steer, AI_motor] =forward_pass(version, solver, ZED_data, meta_data_label)

                        """
                        if AI_motor > 60:
                            AI_motor = (AI_motor-60)/39.0*10.0 + 60
                        """
                        
                        if AI_motor > 50:
                            AI_motor = (AI_motor-50)/39.0*10.0 + 50

                        
                        AI_motor = int((AI_motor-49.) * motor_gain + 49)
                        AI_steer = int((AI_steer-49.) * steer_gain + 49)



                        if AI_motor > 99:
                            AI_motor = 99
                        if AI_motor < 0:
                            AI_motor = 0
                        if AI_steer > 99:
                            AI_steer = 99
                        if AI_steer < 0:
                            AI_steer = 0

                        AI_steer = int((AI_steer+AI_steer_previous)/2.0)
                        AI_steer_previous = AI_steer
                        AI_motor = int((AI_motor+AI_motor_previous)/2.0)
                        AI_motor_previous = AI_motor
                        

                        if AI_motor > motor_freeze_threshold and np.array(encoder_list[0:3]).mean() > 1 and np.array(encoder_list[-3:]).mean()<0.2 and state_transition_time_s > 1:
                            freeze = True

                        
                        if freeze:
                            print "######### FREEZE ###########"
                            AI_steer = 49
                            AI_motor 
                        freeze_cmd_pub.publish(std_msgs.msg.Int32(freeze))

                         
                        if state in [3,6]:            
                            steer_cmd_pub.publish(std_msgs.msg.Int32(AI_steer))
                        
                        if state in [6,7]:
                            motor_cmd_pub.publish(std_msgs.msg.Int32(AI_motor))

                        
                        if True: #verbose:
                            print("{},{},{},{}".format(AI_motor,AI_steer,motor_gain,steer_gain,state))
                            #print AI_motor,AI_steer,motor_gain,steer_gain,state

        else:
            AI_enter_timer.reset()
            if state == 4:
                freeze = False
            if state == 2:
                freeze = False
            if state == 1:
                freeze = False
            if state == 4 and state_transition_time_s > 30:
                print("Shutting down because in state 4 for 30+ s")
                #unix('sudo shutdown -h now')
        if time_step.check():
            print(d2s("In state",state,"for",state_transition_time_s,"seconds, previous_state =",previous_state))
            time_step.reset()
            if not folder_display_timer.check():
                print("*** Data foldername = "+foldername+ '***')
        if reload_timer.check():            
            reload(model_car.car_run_params)
            from model_car.car_run_params import *
            
            model_name_pub.publish(std_msgs.msg.String(weights_file_path))
            reload_timer.reset()

        if git_pull_timer.check():
            #unix(opjh('kzpy3/kzpy3_git_pull.sh'))
            unix(opjh('model_car/model_car_git_pull.sh'))
            git_pull_timer.reset()

except Exception as e:
    print("********** Exception ***********************",'red')
    traceback.print_exc(file=sys.stdout)
    rospy.signal_shutdown(d2s(e.message,e.args))

