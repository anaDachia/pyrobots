import logging; logger = logging.getLogger("novela." + __name__)
logger.setLevel(logging.DEBUG)

import roslib; roslib.load_manifest('novela_actionlib')
import rospy

import actionlib
import move_base_msgs.msg

from helpers.cb import *

from action import action, ros_request


###############################################################################
###############################################################################

@action
def goto(target, callback = None):
	""" Moves the robot base to a given target, using ROS 2D navigation stack.

        Only (x,y,theta) are considered for the target. All other values are
        ignored.
    
        :param target: the destination, as a dictionary {x,y,z,qx,qy,qz,qw}.
        :param callback: (optional) a callback to be called when the destination
        is reached. If nothing is provided, the action blocks until the 
        destination is reached.
	"""
	x = target['x']
	y = target['y']
	z = target['z']
	qx = target['qx']
	qy = target['qy']
	qz = target['qz']
	qw = target['qw']

	# Creates the SimpleActionClient, passing the type of the action
	# (Navigationction) to the constructor.
	client = actionlib.SimpleActionClient('move_base', move_base_msgs.msg.MoveBaseAction)

	ok = client.wait_for_server()
	if not ok:
		#logger.error("Could not connect to the ROS client! Aborting action")
		print("Could not connect to the ROS client! Aborting action")
		return



	# Creates a goal to send to the action server.  
	goal = move_base_msgs.msg.MoveBaseGoal()

	# Definition of the goal
	goal.target_pose.header.frame_id = 'map'
	goal.target_pose.header.stamp = rospy.Time.now();

	goal.target_pose.pose.position.x = x
	goal.target_pose.pose.position.y = y
	goal.target_pose.pose.position.z = z

	goal.target_pose.pose.orientation.x = qx
	goal.target_pose.pose.orientation.y = qy
	goal.target_pose.pose.orientation.z = qz
	goal.target_pose.pose.orientation.w = qw
	
	

	return [ros_request(client, 
			goal, 
			wait_for_completion = False if callback else True,
			callback = callback
		)] # REturn a non-blocking action. Useful to be able to cancel it later!

###############################################################################

@action
def cancel():
	""" Interrupt a navigation task.
	"""
	client = actionlib.SimpleActionClient('move_base', move_base_msgs.msg.MoveBaseAction)
	
	ok = client.wait_for_server()
	if not ok:
		#logger.error("Could not connect to the ROS client! Aborting action")
		print("Could not connect to the ROS client! Aborting action")
		return

	# Creates a goal to send to the action server.  
	goal = move_base_msgs.msg.MoveBaseGoal()

	return [ros_request(client, goal)]



###############################################################################

@action
def carry(target, callback = None):
    """ Moves to a place, taking into account door crossing.

    If the robot needs to cross a door, it will stop in front of the door,
    tuck its arms, cross the door, untuck the arms and complete its route.

    TODO: This action is currently completely hardcoded, and will work only
    for the Novela scenario.

    :param target: the destination, as a dictionary {x,y,z,qx,qy,qz,qw}.
    :param callback: (optional) a callback to be called when the destination
    is reached. If nothing is provided, the action blocks until the 
    destination is reached.
    """

    from helpers import position
    from helpers import places
    from actions import configuration

    mypos = position.mypose()

    target_is_in = position.isonstage(target)
    i_am_in = position.isonstage(mypos)
    if not (target_is_in ^ i_am_in):
        # No door to cross
        return goto(target, callback)
    else:
        # We need to cross a door!
        actions = []

        logger.info("I need to cross a door!!")
        print("I need to cross a door!!")
        
        if i_am_in:
            print("I'm in, I want to go out")
            # I'm in, I want to go out
            actions += configuration.tucked(nop)
            actions += goto(places.read()["JARDIN_EXIT_IN"], callback)
            actions += goto(places.read()["JARDIN_EXIT_OUT"], callback)
            actions += configuration.manip(nop)
            actions += goto(target, callback)

        else:
            print("I'm out, I want to go in")
            # I'm out, I want to go in
            actions += configuration.tucked(nop)
            actions += goto(places.read()["JARDIN_ENTER_OUT"], callback)
            actions += goto(places.read()["JARDIN_ENTER_IN"], callback)
            actions += configuration.manip(nop)
            actions += goto(target, callback)

        return actions

