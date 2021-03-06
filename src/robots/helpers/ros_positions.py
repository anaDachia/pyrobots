import logging; logger = logging.getLogger("robots.position.ros")

import rospy
import tf

from robots.helpers.position import FrameProvider, UnknownFrameError

class ROSFrames(FrameProvider):
    def __init__(self):
        self.tf_running = True

        self.tf = tf.TransformListener()
        self.br = tf.TransformBroadcaster()

        try:
            self.tf.waitForTransform("/base_link", "/map", rospy.Time(), rospy.Duration(1.0))
        except tf.Exception: # likely a timeout
            logger.error("Timeout while waiting for the TF transformation with the map!"
                         " Is someone publishing TF tansforms?\n ROS positions won't be available.")
            self.tf_running = False

    def asROSpose(self, pose):
        """ Returns a ROS PoseStamped from a pyRobots pose.

        :param pose: a standard pyRobots pose (SPARK id, TF frame, [x,y,z],
        [x,y,z,rx,ry,rz], [x,y,z,qx,qy,qw,qz], {'x':..., 'y':...,...})

        :return: the corresponding ROS PoseStamped
        """

        from geometry_msgs.msg import PoseStamped
        import rospy

        poseStamped = PoseStamped()

        poseStamped.header.frame_id = pose["frame"]
        poseStamped.header.stamp = self.tf.getLatestCommonTime("/map", pose["frame"])
        poseStamped.pose.position.x = pose["x"]
        poseStamped.pose.position.y = pose["y"]
        poseStamped.pose.position.z = pose["z"]
        poseStamped.pose.orientation.x = pose["qx"]
        poseStamped.pose.orientation.y = pose["qy"]
        poseStamped.pose.orientation.z = pose["qz"]
        poseStamped.pose.orientation.w = pose["qw"]

        return poseStamped

    def publish_transform(self, name, pose):
        """
        Publishes a new TF frame called 'name' based on the pyRobots transform 'pose'.

        Note that this function *does not* normalize the input pose, which must already
        be a dictionary with the keys [x,y,z,qx,qy,qz,qw,frame].
        """
        self.br.sendTransform((pose["x"], pose["y"], pose["z"]),
                              (pose["qx"], pose["qy"], pose["qz"], pose["qw"]),
                              rospy.Time.now(),
                              name,
                              pose["frame"])

    def inframe(self, pose, frame):
        """ Transforms a given pose in the given frame.
        """
        if not self.tf_running:
            raise UnknownFrameError("TF not running")


        poseStamped = self.asROSpose(pose)
        if self.tf.frameExists(frame) and self.tf.frameExists(poseStamped.header.frame_id):

            newPoseStamped = self.tf.transformPose(frame, poseStamped)

            return {"x":newPoseStamped.pose.position.x,
                    "y":newPoseStamped.pose.position.y,
                    "z":newPoseStamped.pose.position.z,
                    "qx":newPoseStamped.pose.orientation.x,
                    "qy":newPoseStamped.pose.orientation.y,
                    "qz":newPoseStamped.pose.orientation.z,
                    "qw":newPoseStamped.pose.orientation.w,
                    "frame": frame}

        logger.error("Could not transform the pose from %s to %s." % (poseStamped.header.frame_id, frame))
        raise UnknownFrameError("Frame %s not known by TF" % frame)

    def get_transform(self, frame):

        if not self.tf_running:
            raise UnknownFrameError("TF not running")

        if self.tf.frameExists(frame) and self.tf.frameExists("/map"):
            t = self.tf.getLatestCommonTime("/map", frame)
            position, quaternion = self.tf.lookupTransform("/map", frame, t)
            return dict(zip(["x","y","z","qx","qy","qz","qw","frame"], position + quaternion + ("map",)))

        logger.error("Could not read the pose of " + frame + " in /map")
        raise UnknownFrameError("Frame %s not known by TF" % frame)

