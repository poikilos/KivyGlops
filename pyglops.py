"""
This provides simple dependency-free access to OBJ files and certain 3D math operations.
#Illumination models (as per OBJ format standard) [NOT YET IMPLEMENTED]:
# 0. Color on and Ambient off
# 1. Color on and Ambient on [binary:0001]
# 2. Highlight on [binary:0010]
# 3. Reflection on and Ray trace on [binary:0011]
# 4. Transparency: Glass on, Reflection: Ray trace on [binary:0100]
# 5. Reflection: Fresnel on and Ray trace on [binary:0101]
# 6. Transparency: Refraction on, Reflection: Fresnel off and Ray trace on [binary:0110]
# 7. Transparency: Refraction on, Reflection: Fresnel on and Ray trace on [binary:0111]
# 8. Reflection on and Ray trace off [binary:1000]
# 9. Transparency: Glass on, Reflection: Ray trace off [binary:1001]
# 10. Casts shadows onto invisible surfaces [binary:1010]
"""

import os
import math
#from docutils.utils.math.math2html import VerticalSpace
#import traceback
from common import *

#references:
#kivy-trackball objloader (version with no MTL loader) by nskrypnik
#objloader from kivy-rotation3d (version with placeholder mtl loader) by nskrypnik

#TODO:
#-remove resource_find but still make able to find mtl file under Kivy somehow

from kivy.resources import resource_find
from wobjfile import *
dump_enable = False
add_dump_comments_enable = False

V_POS_INDEX = 0
V_TC0_INDEX = 1
V_TC1_INDEX = 2
V_DIFFUSE_INDEX = 3
V_NORMAL_INDEX = 4
#see also pyglopsmesh.vertex_depth below

#indices of tuples inside vertex_format (see PyGlop)
VFORMAT_NAME_INDEX = 0
VFORMAT_VECTOR_LEN_INDEX = 1
VFORMAT_TYPE_INDEX = 2

EMPTY_ITEM = dict()
EMPTY_ITEM["name"] = "Empty"

kEpsilon = 1.0E-14 # adjust to suit.  If you use floats, you'll probably want something like 1E-7f

def get_vec3_from_point(point):
    return (point.x, point.y, point.z)

def get_rect_from_polar_deg(r, theta):
    x = r * math.cos(math.radians(theta))
    y = r * math.sin(math.radians(theta))
    return x,y

def get_rect_from_polar_rad(r, theta):
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return x,y

def angle_trunc(a):
    while a < 0.0:
        a += math.pi * 2
    return a
# angle_trunc and getAngleBetweenPoints edited Jul 19 '15 at 20:12  answered Sep 28 '11 at 16:10  Peter O. <http://stackoverflow.com/questions/7586063/how-to-calculate-the-angle-between-a-line-and-the-horizontal-axis>. 29 Apr 2016
def getAngleBetweenPoints(x_orig, y_orig, x_landmark, y_landmark):
    deltaY = y_landmark - y_orig
    deltaX = x_landmark - x_orig
    return angle_trunc(math.atan2(deltaY, deltaX))

#get angle between two points (from a to b), swizzled to 2d on xz plane; based on getAngleBetweenPoints
def get_angle_between_two_vec3_xz(a, b):
    deltaY = b[2] - a[2]
    deltaX = b[0] - a[0]
    return angle_trunc(math.atan2(deltaY, deltaX))

#returns nearest point on line bc from point a, swizzled to 2d on xz plane
def get_nearest_vec3_on_vec3line_using_xz(a, b, c): #formerly PointSegmentDistanceSquared
    t = None
    #as per http://stackoverflow.com/questions/849211/shortest-distance-between-a-point-and-a-line-segment
    kMinSegmentLenSquared = 0.00000001 # adjust to suit.  If you use float, you'll probably want something like 0.000001f

    #epsilon is the common name for the floating point error constant (needed since some base 10 numbers cannot be stored as IEEE 754 with absolute precision)
    #same as 1.0 * 10**-14 according to http://python-reference.readthedocs.io/en/latest/docs/float/scientific.html
    dx = c[0] - b[0]
    dy = c[2] - b[2]
    db = [a[0] - b[0], 0.0, a[2] - b[2]]  # 0.0 since swizzling to xz (ignore source y)
    segLenSquared = (dx * dx) + (dy * dy)
    if segLenSquared >= -kMinSegmentLenSquared and segLenSquared <= kMinSegmentLenSquared:
        # segment is a point.
        qx = b[0]
        qy = b[2]
        t = 0.0
        distance = ((db[0] * db[0]) + (db[2] * db[2]))
        return qx, a[1], qy, distance
    else:
        # Project a line from p to the segment [p1,p2].  By considering the line
        # extending the segment, parameterized as p1 + (t * (p2 - p1)),
        # we find projection of point p onto the line.
        # It falls where t = [(p - p1) . (p2 - p1)] / |p2 - p1|^2
        t = ((db[0] * dx) + (db[2] * dy)) / segLenSquared
        if t < kEpsilon:
            # intersects at or to the "left" of first segment vertex (b[0], b[2]).  If t is approximately 0.0, then
            # intersection is at p1.  If t is less than that, then there is no intersection (i.e. p is not within
            # the 'bounds' of the segment)
            if t > -kEpsilon:
                # intersects at 1st segment vertex
                t = 0.0
            # set our 'intersection' point to p1.
            qx = b[0]
            qy = b[2]
        elif t > (1.0 - kEpsilon): # Note: If you wanted the ACTUAL intersection point of where the projected lines would intersect if
        # we were doing PointLineDistanceSquared, then qx would be (b[0] + (t * dx)) and qy would be (b[2] + (t * dy)).

            # intersects at or to the "right" of second segment vertex (c[0], c[2]).  If t is approximately 1.0, then
            # intersection is at p2.  If t is greater than that, then there is no intersection (i.e. p is not within
            # the 'bounds' of the segment)
            if t < (1.0 + kEpsilon):
                # intersects at 2nd segment vertex
                t = 1.0
            # set our 'intersection' point to p2.
            qx = c[0]
            qy = c[2]
        else:
            # Note: If you wanted the ACTUAL intersection point of where the projected lines would intersect if
            # we were doing PointLineDistanceSquared, then qx would be (b[0] + (t * dx)) and qy would be (b[2] + (t * dy)).
            # The projection of the point to the point on the segment that is perpendicular succeeded and the point
            # is 'within' the bounds of the segment.  Set the intersection point as that projected point.
            qx = b[0] + (t * dx)
            qy = b[2] + (t * dy)
        # return the squared distance from p to the intersection point.  Note that we return the squared distance
        # as an oaimization because many times you just need to compare relative distances and the squared values
        # works fine for that.  If you want the ACTUAL distance, just take the square root of this value.
        dpqx = a[0] - qx
        dpqy = a[2] - qy
        distance = ((dpqx * dpqx) + (dpqy * dpqy))
        return qx, a[1], qy, distance


#returns distance from point a to line bc, swizzled to 2d on xz plane
def get_distance_vec2_to_vec2line_xz(a, b, c):
    return math.sin(math.atan2(b[2] - a[2], b[0] - a[0]) - math.atan2(c[2] - a[2], c[0] - a[0])) * math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[2] - a[2]) * (b[2] - a[2]))

#returns distance from point a to line bc
def get_distance_vec2_to_vec2line(a, b, c):
    #from ADOConnection on stackoverflow answered Nov 18 '13 at 22:37
    #this commented part is the expanded version of the same answer (both versions are given in answer)
    #// normalize points
    #Point cn = new Point(c[0] - a[0], c[1] - a[1]);
    #Point bn = new Point(b[0] - a[0], b[1] - a[1]);

    #double angle = Math.Atan2(bn[1], bn[0]) - Math.Atan2(cn[1], cn[0]);
    #double abLength = Math.Sqrt(bn[0]*bn[0] + bn[1]*bn[1]);

    #return math.sin(angle)*abLength;
    return math.sin(math.atan2(b[1] - a[1], b[0] - a[0]) - math.atan2(c[1] - a[1], c[0] - a[0])) * math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1]))

#swizzle to 2d point on xz plane, then get distance
def get_distance_vec3_xz(first_pt, second_pt):
    return math.sqrt( (second_pt[0]-first_pt[0])**2 + (second_pt[2]-first_pt[2])**2 )

def get_distance_vec3(first_pt, second_pt):
    return math.sqrt((second_pt[0] - first_pt[0])**2 + (second_pt[1] - first_pt[1])**2 + (second_pt[2] - first_pt[2])**2)

def get_distance_vec2(first_pt, second_pt):
    return math.sqrt( (second_pt[0]-first_pt[0])**2 + (second_pt[1]-first_pt[1])**2 )

#halfplane check (which half) formerly sign
def get_halfplane_sign(p1, p2, p3):
    #return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y);
    return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1]);
#PointInTriangle and sign are from http://stackoverflow.com/questions/2049582/how-to-determine-a-point-in-a-2d-triangle
#edited Oct 18 '14 at 18:52 by msrd0
#answered Jan 12 '10 at 14:27 by Kornel Kisielewicz
#(based on http://www.gamedev.net/community/forums/topic.asp?topic_id=295943)
def PointInTriangle(pt, v1, v2, v3):
    b1 = get_halfplane_sign(pt, v1, v2) < 0.0
    b2 = get_halfplane_sign(pt, v2, v3) < 0.0
    b3 = get_halfplane_sign(pt, v3, v1) < 0.0
    #WARNING: returns false sometimes on edge, depending whether triangle is clockwise or counter-clockwise
    return (b1 == b2) and (b2 == b3)

def get_pushed_vec3_xz_rad(pos, r, theta):
    #push_x, push_y = (0,0)
    #if r != 0:
    push_x, push_y = get_rect_from_polar_rad(r, theta)
    return pos[0]+push_x, pos[1], pos[2]+push_y

#3 vector version of Developer's solution to <http://stackoverflow.com/questions/2049582/how-to-determine-a-point-in-a-2d-triangle> answered Jan 6 '14 at 11:32 by Developer
#uses x and y values
def is_in_triangle_HALFPLANES(check_pt,v0, v1, v2):
    '''checks if point check_pt(2) is inside triangle tri(3x2). @Developer'''
    a = 1/(-v1[1]*v2[0]+v0[1]*(-v1[0]+v2[0])+v0[0]*(v1[1]-v2[1])+v1[0]*v2[1])
    s = a*(v2[0]*v0[1]-v0[0]*v2[1]+(v2[1]-v0[1])*check_pt[0]+(v0[0]-v2[0])*check_pt[1])
    if s<0: return False
    else: t = a*(v0[0]*v1[1]-v1[0]*v0[1]+(v0[1]-v1[1])*check_pt[0]+(v1[0]-v0[0])*check_pt[1])
    return ((t>0) and (1-s-t>0))

def is_in_triangle_HALFPLANES_xz(check_pt,v0, v1, v2):
    '''checks if point check_pt(2) is inside triangle tri(3x2). @Developer'''
    a = 1/(-v1[2]*v2[0]+v0[2]*(-v1[0]+v2[0])+v0[0]*(v1[2]-v2[2])+v1[0]*v2[2])
    s = a*(v2[0]*v0[2]-v0[0]*v2[2]+(v2[2]-v0[2])*check_pt[0]+(v0[0]-v2[0])*check_pt[2])
    if s<0: return False
    else: t = a*(v0[0]*v1[2]-v1[0]*v0[2]+(v0[2]-v1[2])*check_pt[0]+(v1[0]-v0[0])*check_pt[2])
    return ((t>0) and (1-s-t>0))

#float calcY(vec3 p1, vec3 p2, vec3 p3, float x, float z) {
# as per http://stackoverflow.com/questions/5507762/how-to-find-z-by-arbitrary-x-y-coordinates-within-triangle-if-you-have-triangle
#  edited Jan 21 '15 at 15:07 josh2112 answered Apr 1 '11 at 0:02 Martin Beckett
def get_y_from_xz(p1, p2, p3, x, z):
    det = (p2[2] - p3[2]) * (p1[0] - p3[0]) + (p3[0] - p2[0]) * (p1[2] - p3[2]);

    l1 = ((p2[2] - p3[2]) * (x - p3[0]) + (p3[0] - p2[0]) * (z - p3[2])) / det;
    l2 = ((p3[2] - p1[2]) * (x - p3[0]) + (p1[0] - p3[0]) * (z - p3[2])) / det;
    l3 = 1.0 - l1 - l2;

    return l1 * p1[1] + l2 * p2[1] + l3 * p3[1];

#Did not yet read article: http://totologic.blogspot.fr/2014/01/accurate-point-in-triangle-test.html

#Developer's solution to <http://stackoverflow.com/questions/2049582/how-to-determine-a-point-in-a-2d-triangle> answered Jan 6 '14 at 11:32 by Developer
def PointInsideTriangle2_vec2(check_pt,tri):
    '''checks if point check_pt(2) is inside triangle tri(3x2). @Developer'''
    a = 1/(-tri[1,1]*tri[2,0]+tri[0,1]*(-tri[1,0]+tri[2,0])+tri[0,0]*(tri[1,1]-tri[2,1])+tri[1,0]*tri[2,1])
    s = a*(tri[2,0]*tri[0,1]-tri[0,0]*tri[2,1]+(tri[2,1]-tri[0,1])*check_pt[0]+(tri[0,0]-tri[2,0])*check_pt[1])
    if s<0: return False
    else: t = a*(tri[0,0]*tri[1,1]-tri[1,0]*tri[0,1]+(tri[0,1]-tri[1,1])*check_pt[0]+(tri[1,0]-tri[0,0])*check_pt[1])
    return ((t>0) and (1-s-t>0))

def is_in_triangle_coords(px, py, p0x, p0y, p1x, p1y, p2x, p2y):
#    IsInTriangle_Barymetric
    kEpsilon = 1.0E-14 # adjust to suit.  If you use floats, you'll probably want something like 1E-7f (added by expertmm)
    Area = 1/2*(-p1y*p2x + p0y*(-p1x + p2x) + p0x*(p1y - p2y) + p1x*p2y)
    s = 1/(2*Area)*(p0y*p2x - p0x*p2y + (p2y - p0y)*px + (p0x - p2x)*py)
    t = 1/(2*Area)*(p0x*p1y - p0y*p1x + (p0y - p1y)*px + (p1x - p0x)*py)
#    #TODO: fix situation where it fails when clockwise (see discussion at http://stackoverflow.com/questions/2049582/how-to-determine-a-point-in-a-2d-triangle )
    return  s>kEpsilon and t>kEpsilon and 1-s-t>kEpsilon

#swizzled to xz (uses index 0 and 2 of vec3)
def is_in_triangle_xz(check_vec3, a_vec3, b_vec3, c_vec3):
#    IsInTriangle_Barymetric
    kEpsilon = 1.0E-14 # adjust to suit.  If you use floats, you'll probably want something like 1E-7f (added by expertmm)
    Area = 1/2*(-b_vec3[2]*c_vec3[0] + a_vec3[2]*(-b_vec3[0] + c_vec3[0]) + a_vec3[0]*(b_vec3[2] - c_vec3[2]) + b_vec3[0]*c_vec3[2])
    s = 1/(2*Area)*(a_vec3[2]*c_vec3[0] - a_vec3[0]*c_vec3[2] + (c_vec3[2] - a_vec3[2])*check_vec3[0] + (a_vec3[0] - c_vec3[0])*check_vec3[2])
    t = 1/(2*Area)*(a_vec3[0]*b_vec3[2] - a_vec3[2]*b_vec3[0] + (a_vec3[2] - b_vec3[2])*check_vec3[0] + (b_vec3[0] - a_vec3[0])*check_vec3[2])
#    #TODO: fix situation where it fails when clockwise (see discussion at http://stackoverflow.com/questions/2049582/how-to-determine-a-point-in-a-2d-triangle )
    return  s>kEpsilon and t>kEpsilon and 1-s-t>kEpsilon

#swizzled to xz (uses index 0 and 2 of vec3)
def is_in_triangle_vec2(check_vec2, a_vec2, b_vec2, c_vec2):
#    IsInTriangle_Barymetric
    kEpsilon = 1.0E-14 # adjust to suit.  If you use floats, you'll probably want something like 1E-7f (added by expertmm)
    Area = 1/2*(-b_vec2[1]*c_vec2[0] + a_vec2[1]*(-b_vec2[0] + c_vec2[0]) + a_vec2[0]*(b_vec2[1] - c_vec2[1]) + b_vec2[0]*c_vec2[1])
    if Area>kEpsilon or Area<-kEpsilon:
        s = 1/(2*Area)*(a_vec2[1]*c_vec2[0] - a_vec2[0]*c_vec2[1] + (c_vec2[1] - a_vec2[1])*check_vec2[0] + (a_vec2[0] - c_vec2[0])*check_vec2[1])
        t = 1/(2*Area)*(a_vec2[0]*b_vec2[1] - a_vec2[1]*b_vec2[0] + (a_vec2[1] - b_vec2[1])*check_vec2[0] + (b_vec2[0] - a_vec2[0])*check_vec2[1])
    #    #TODO: fix situation where it fails when clockwise (see discussion at http://stackoverflow.com/questions/2049582/how-to-determine-a-point-in-a-2d-triangle )
        return  s>kEpsilon and t>kEpsilon and 1-s-t>kEpsilon
    else:
        return False
#class ItemData:  #changed to dict
#    name = None
#    passive_bumper_command = None
#    health_ratio = None

#    def __init__(self, bump="obtain"):
#        health_ratio = 1.0
#        passive_bumper_command = bump

# PyGlop defines a single OpenGL-ready object. PyGlops should be used for importing, since one mesh file (such as obj) can contain several meshes. PyGlops handles the 3D scene.

class PyGlopHitBox:
    minimums = None
    maximums = None

    def __init__(self):
        self.minimums = [-0.25, -0.25, -0.25]
        self.maximums = [0.25, 0.25, 0.25]

    def contains_vec3(self, pos):
        return pos[0]>=self.minimums[0] and pos[0]<=self.maximums[0] \
            and pos[1]>=self.minimums[1] and pos[1]<=self.maximums[1] \
            and pos[2]>=self.minimums[2] and pos[2]<=self.maximums[2]

    def to_string(self):
        return str(self.minimums[0]) + " to " + str(self.maximums[0]) + \
            ",  "+str(self.minimums[1]) + " to " + str(self.maximums[1]) + \
            ",  " + str(self.minimums[2])+" to "+str(self.maximums[2])


class PyGlop:
    name = None #object name such as from OBJ's 'o' statement
    source_path = None  #required so that meshdata objects can be uniquely identified (where more than one file has same object name)
    properties = None #dictionary of properties--has indices such as usemtl
    vertex_depth = None
    material = None
    _min_coords = None  #bounding cube minimums in local coordinates
    _max_coords = None  #bounding cube maximums in local coordinates
    _pivot_point = None  #TODO: asdf eliminate this--instead always use 0,0,0 and move vertices to change pivot; currently calculated from average of vertices if was imported from obj
    foot_reach = None  # distance from center (such as root bone) to floor
    eye_height = None  # distance from floor
    hit_radius = None
    item_dict = None
    projectile_dict = None
    actor_dict = None
    bump_enable = None
    reach_radius = None
    is_out_of_range = None
    physics_enable = None
    x_velocity = None
    y_velocity = None
    z_velocity = None
    _cached_floor_y = None
    infinite_inventory_enable = None
    bump_sounds = None
    look_target_glop = None
    hitbox = None
    visible_enable = None
    #IF ADDING NEW VARIABLE here, remember to update any copy constructors in your subclass or calling program

    #region runtime variables
    index = None  # set by add_glop
    #endregion runtime variables

    vertex_format = None
    vertices = None
    indices = None
    #opacity = None  moved to material.diffuse_color 4th channel

    #region vars based on OpenGL ES 1.1 MOVED TO material
    #ambient_color = None  # vec4
    #diffuse_color = None  # vec4
    #specular_color = None  # vec4
    ##emissive_color = None  # vec4
    #specular_exponent = None  # float
    #endregion vars based on OpenGL ES 1.1 MOVED TO material

    #region calculated from vertex_format
    _POSITION_OFFSET = None
    _NORMAL_OFFSET = None
    _TEXCOORD0_OFFSET = None
    _TEXCOORD1_OFFSET = None
    COLOR_OFFSET = None
    POSITION_INDEX = None
    NORMAL_INDEX = None
    TEXCOORD0_INDEX = None
    TEXCOORD1_INDEX = None
    COLOR_INDEX = None
    #endregion calculated from vertex_format

    def __init__(self):
        self.visible_enable = True
        self.hitbox = PyGlopHitBox()
        self.physics_enable = False
        self.infinite_inventory_enable = True
        self.is_out_of_range = True
        self.hit_radius = 0.1524  # .5' equals .1524m
        self.reach_radius = 0.381 # 2.5' .381m
        self.bump_enable = False
        self.x_velocity = 0.0
        self.y_velocity = 0.0
        self.z_velocity = 0.0
        self.bump_sounds = []
        self.properties = {}
        self.properties["inventory_index"] = -1
        self.properties["inventory_items"] = []
        #formerly in MeshData:
        # order MUST match V_POS_INDEX etc above
        self.vertex_format = [
            (b'a_position', 4, 'float'),  # Munshi prefers vec4 (Kivy prefers vec3)
            (b'a_texcoord0', 4, 'float'),  # Munshi prefers vec4 (Kivy prefers vec2); vTexCoord0; available if enable_tex[0] is true
            (b'a_texcoord1', 4, 'float'),  # Munshi prefers vec4 (Kivy prefers vec2);  available if enable_tex[1] is true
            (b'a_color', 4, 'float'),  # vColor (diffuse color of vertex)
            (b'a_normal', 3, 'float')  # vNormal; Munshi prefers vec3 (Kivy also prefers vec3)
            ]
        self.vertex_depth = 0
        for i in range(0,len(self.vertex_format)):
            self.vertex_depth += self.vertex_format[i][VFORMAT_VECTOR_LEN_INDEX]

        self.on_vertex_format_change()

        self.indices = []  # list of tris (vertex index, vertex index, vertex index, etc)

        # Default basic material of this glop
        self.material = PyGlopsMaterial()
        self.material.diffuse_color = (1.0, 1.0, 1.0, 1.0)  # overlay vertex color onto this using vertex alpha
        self.material.ambient_color = (0.0, 0.0, 0.0, 1.0)
        self.material.specular_color = (1.0, 1.0, 1.0, 1.0)
        self.material.specular_coefficent = 16.0
        #self.material.opacity = 1.0

        #TODO: find out where this code goes (was here for unknown reason)
        #if result is None:
        #    print("WARNING: no material for Glop named '"+str(self.name)+"' (NOT YET IMPLEMENTED)")
        #return result


    def calculate_hit_range(self):
        print("Calculate hit range should be implemented by subclass.")
        print("  (setting hitbox to None to avoid using default hitbox)")
        self.hitbox = None
    
    def process_ai(self, glop_index):
        #this should be implemented in the subclass
        pass

    def apply_pivot(self):
        vertex_count = int(len(self.vertices)/self.vertex_depth)
        v_offset = 0
        for i in range(0,3):
            #intentionally set to rediculously far in opposite direction:
            self.hitbox.minimums[i] = sys.maxsize
            self.hitbox.maximums[i] = -sys.maxsize
        for v_number in range(0, vertex_count):
            for i in range(0,3):
                self.vertices[v_offset+self._POSITION_OFFSET+i] -= self._pivot_point[i]
                if self.vertices[v_offset+self._POSITION_OFFSET+i] < self.hitbox.minimums[i]:
                    self.hitbox.minimums[i] = self.vertices[v_offset+self._POSITION_OFFSET+i]
                if self.vertices[v_offset+self._POSITION_OFFSET+i] > self.hitbox.maximums[i]:
                    self.hitbox.maximums[i] = self.vertices[v_offset+self._POSITION_OFFSET+i]
            this_vertex_relative_distance = get_distance_vec3(self.vertices[v_offset+self._POSITION_OFFSET:], self._pivot_point)
            if this_vertex_relative_distance > self.hit_radius:
                self.hit_radius = this_vertex_relative_distance
            #self.vertices[v_offset+self._POSITION_OFFSET+0] -= self._pivot_point[0]
            #self.vertices[v_offset+self._POSITION_OFFSET+1] -= self._pivot_point[1]
            #self.vertices[v_offset+self._POSITION_OFFSET+2] -= self._pivot_point[2]

            v_offset += self.vertex_depth
        self._pivot_point = (0.0, 0.0, 0.0)

    def look_at(self, this_glop):
        print("WARNING: look_at should be implemented by subclass which has rotation angle(s) or matr(ix/ices)")
        
    def has_item(self, name):
        result = False
        for i in range(0,len(self.properties["inventory_items"])):
            if (self.properties["inventory_items"][i] is not None) and \
               (self.properties["inventory_items"][i]["name"] == name):
                result = True
                break
        return result

    def push_item(self, item_dict):
        select_item_event_dict = dict()
        select_item_event_dict["is_possible"] = False
        for i in range(0,len(self.properties["inventory_items"])):
            if self.properties["inventory_items"][i] is None or self.properties["inventory_items"][i]["name"] == EMPTY_ITEM["name"]:
                self.properties["inventory_items"][i] = item_dict
                select_item_event_dict["is_possible"] = True
                #print("obtained item in slot "+str(i)+": "+str(item_dict))
                break
        if self.infinite_inventory_enable:
            if not select_item_event_dict["is_possible"]:
                self.properties["inventory_items"].append(item_dict)
                #print("obtained item in new slot: "+str(item_dict))
                select_item_event_dict["is_possible"] = True
        if select_item_event_dict["is_possible"]:
            if self.properties["inventory_index"] < 0:
                self.properties["inventory_index"] = 0
            this_item_dict = self.properties["inventory_items"][self.properties["inventory_index"]]
            name = ""
            proper_name = ""
            select_item_event_dict["inventory_index"] = self.properties["inventory_index"]
            if "name" in this_item_dict:
                name = this_item_dict["name"]
            select_item_event_dict["name"] = name
            if "glop_name" in this_item_dict:
                proper_name = this_item_dict["glop_name"]
            select_item_event_dict["proper_name"] = proper_name
            select_item_event_dict["calling method"] = "push_glop_item"
        return select_item_event_dict


    def select_next_inventory_slot(self, is_forward):
        select_item_event_dict = dict()
        delta = 1
        if not is_forward:
            delta = -1
        if len(self.properties["inventory_items"]) > 0:
            select_item_event_dict["is_possible"] = True
            self.properties["inventory_index"] += delta
            if self.properties["inventory_index"] < 0:
                self.properties["inventory_index"] = len(self.properties["inventory_items"]) - 1
            elif self.properties["inventory_index"] >= len(self.properties["inventory_items"]):
                self.properties["inventory_index"] = 0
            this_item_dict = self.properties["inventory_items"][self.properties["inventory_index"]]
            name = ""
            proper_name = ""
            select_item_event_dict["inventory_index"] = self.properties["inventory_index"]
            if "glop_name" in this_item_dict:
                proper_name = this_item_dict["glop_name"]
            select_item_event_dict["proper_name"] = proper_name
            if "name" in this_item_dict:
                name = this_item_dict["name"]
            select_item_event_dict["name"] = name
            #print("item event: "+str(select_item_event_dict))
            select_item_event_dict["calling method"] = "select_next_inventory_slot"
            #print("Selected "+this_item_dict["name"]+" "+proper_name+" in slot "+str(self.properties["inventory_index"]))
            item_count = 0
            for index in range(0, len(self.properties["inventory_items"])):
                if self.properties["inventory_items"][index]["name"] != EMPTY_ITEM["name"]:
                    item_count += 1
            #print("You have "+str(item_count)+" item(s).")
            select_item_event_dict["item_count"] = item_count
        else:
            select_item_event_dict["is_possible"] = False
            print("You have 0 items.")
        return select_item_event_dict

    def _on_change_pivot(self):
        pass
    
    def get_context(self):
        print("WARNING: get_context should be defined by a subclass since it involves the graphics implementation")
        return False
    
    def transform_pivot_to_geometry(self):
        self._pivot_point = self.get_center_average_of_vertices()
        self._on_change_pivot()

    def get_texture_diffuse_path(self):  #formerly getTextureFileName(self):
        result = None
        try:
            if self.material is not None:
                if self.material.properties is not None:
                    if "diffuse_path" in self.material.properties:
                        result = self.material.properties["diffuse_path"]
                        if not os.path.exists(result):
                            try_path = os.path.join(os.path.dirname(os.path.abspath(self.source_path)), result)  #
                            if os.path.exists(try_path):
                                result = try_path
                            else:
                                print("Could not find texture (tried '"+str(try_path)+"'")
        except:
            print("Could not finish get_texture_diffuse_path:")
            view_traceback()
        if result is None:
            if verbose_enable:
                print("NOTE: no diffuse texture specified in Glop named '"+str(self.name)+"'")
        return result

    def get_min_x(self):
        val = 0.0
        try:
            val = self._min_coords[0]
        except:
            pass
        return val

    def get_max_x(self):
        val = 0.0
        try:
            val = self._max_coords[0]
        except:
            pass
        return val

    def get_min_y(self):
        val = 0.0
        try:
            val = self._min_coords[1]
        except:
            pass
        return val

    def get_max_y(self):
        val = 0.0
        try:
            val = self._max_coords[1]
        except:
            pass
        return val

    def get_min_z(self):
        val = 0.0
        try:
            val = self._min_coords[2]
        except:
            pass
        return val

    def get_max_z(self):
        val = 0.0
        try:
            val = self._max_coords[2]
        except:
            pass
        return val

    def recalculate_bounds(self):
        self._min_coords = [None,None,None]
        self._max_coords = [None,None,None]
        participle = "initializing"
        try:
            if (self.vertices is not None):
                participle = "accessing vertices"
                for i in range(0,int(len(self.vertices)/self.vertex_depth)):
                    for axisIndex in range(0,3):
                        if self._min_coords[axisIndex] is None or self.vertices[i*self.vertex_depth+axisIndex] < self._min_coords[axisIndex]:
                            self._min_coords[axisIndex] = self.vertices[i*self.vertex_depth+axisIndex]
                        if self._max_coords[axisIndex] is None or self.vertices[i*self.vertex_depth+axisIndex] > self._max_coords[axisIndex]:
                            self._max_coords[axisIndex] = self.vertices[i*self.vertex_depth+axisIndex]
        except:  # Exception as e:
            print("Could not finish "+participle+" in recalculate_bounds: ")
            view_traceback()

    def get_center_average_of_vertices(self):
        #results = (0.0,0.0,0.0)
        totals = list()
        counts = list()
        results = list()
        for i in range(0,self.vertex_format[self.POSITION_INDEX][VFORMAT_VECTOR_LEN_INDEX]):
            if i<3:
                results.append(0.0)
            else:
                results.append(1.0)  #4th index (index 3) must be 1.0 for matrix math to work correctly
        participle = "before initializing"
        try:
            totals.append(0.0)
            totals.append(0.0)
            totals.append(0.0)
            counts.append(0)
            counts.append(0)
            counts.append(0)
            if (self.vertices is not None):
                participle = "accessing vertices"
                for i in range(0,int(len(self.vertices)/self.vertex_depth)):
                    for axisIndex in range(0,3):
                        participle = "accessing vertex axis"
                        if (self.vertices[i*self.vertex_depth+axisIndex]<0):
                            participle = "accessing totals"
                            totals[axisIndex] += self.vertices[i*self.vertex_depth+axisIndex]
                            participle = "accessing vertex count"
                            counts[axisIndex] += 1
                        else:
                            participle = "accessing totals"
                            totals[axisIndex] += self.vertices[i*self.vertex_depth+axisIndex]
                            participle = "accessing vertex count"
                            counts[axisIndex] += 1
            for axisIndex in range(0,3):
                participle = "accessing final counts"
                if (counts[axisIndex]>0):
                    participle = "calculating results"
                    results[axisIndex] = totals[axisIndex] / counts[axisIndex]
        except:  # Exception as e:
            print("Could not finish "+participle+" in get_center_average_of_vertices: ")
            view_traceback()

        return tuple(results)


    def set_textures_from_mtl_dict(self, mtl_dict):
        #print("")
        #print("set_textures_from_mtl_dict...")
        #print("")
        try:
            self.material.diffuse_color = mtl_dict.get('Kd') or self.material.diffuse_color
            self.material.diffuse_color = [float(v) for v in self.material.diffuse_color]
            self.material.ambient_color = mtl_dict.get('Ka') or self.material.ambient_color
            self.material.ambient_color = [float(v) for v in self.material.ambient_color]
            self.material.specular_color = mtl_dict.get('Ks') or self.material.specular_color
            self.material.specular_color = [float(v) for v in self.material.specular_color]
            self.material.specular_coefficent = float(mtl_dict.get('Ns', self.material.specular_coefficent))
            #TODO: store as diffuse color alpha instead: self.opacity = mtl_dict.get('d')
            #TODO: store as diffuse color alpha instead: if self.opacity is None:
            #TODO: store as diffuse color alpha instead:     self.opacity = 1.0 - float(mtl_dict.get('Tr', 0.0))
            if "map_Kd" in mtl_dict.keys():
                self.material.properties["diffuse_path"] = mtl_dict["map_Kd"]
                #print("  NOTE: diffuse_path: "+self.material.properties["diffuse_path"])
            #else:
                #print("  WARNING: "+str(self.name)+" has no map_Kd among material keys "+','.join(mtl_dict.keys()))

        except:  # Exception:
            print("Could not finish set_textures_from_mtl_dict:")
            view_traceback()

    #def calculate_normals(self):
        ##this does not work. The call to calculate_normals is even commented out at <https://github.com/kivy/kivy/blob/master/examples/3Drendering/objloader.py> 20 Mar 2014. 16 Apr 2015.
        #for i in range(int(len(self.indices) / (self.vertex_depth))):
            #fi = i * self.vertex_depth
            #v1i = self.indices[fi]
            #v2i = self.indices[fi + 1]
            #v3i = self.indices[fi + 2]

            #vs = self.vertices
            #p1 = [vs[v1i + c] for c in range(3)]
            #p2 = [vs[v2i + c] for c in range(3)]
            #p3 = [vs[v3i + c] for c in range(3)]

            #u,v  = [0,0,0], [0,0,0]
            #for j in range(3):
                #v[j] = p2[j] - p1[j]
                #u[j] = p3[j] - p1[j]

            #n = [0,0,0]
            #n[0] = u[1] * v[2] - u[2] * v[1]
            #n[1] = u[2] * v[0] - u[0] * v[2]
            #n[2] = u[0] * v[1] - u[1] * v[0]

            #for k in range(3):
                #self.vertices[v1i + 3 + k] = n[k]
                #self.vertices[v2i + 3 + k] = n[k]
                #self.vertices[v3i + 3 + k] = n[k]

    def append_dump(self, thisList, this_min_tab):
        thisList.append(this_min_tab+"Glop:")
        tabString="  "
        if self.name is not None:
            thisList.append(this_min_tab+tabString+"name: "+self.name)
        if self.vertices is not None:
            if add_dump_comments_enable:
                thisList.append(this_min_tab+tabString+"#len(self.vertices)/self.vertex_depth:")
            thisList.append(this_min_tab+tabString+"vertices_count: "+str(len(self.vertices)/self.vertex_depth))
        if self.indices is not None:
            thisList.append(this_min_tab+tabString+"indices_count:"+str(len(self.indices)))
        thisList.append(this_min_tab+tabString+"vertex_depth: "+str(self.vertex_depth))
        if self.vertices is not None:
            if add_dump_comments_enable:
                thisList.append(this_min_tab+tabString+"#len(self.vertices):")
            thisList.append(this_min_tab+tabString+"vertices_info_len: "+str(len(self.vertices)))
        thisList.append(this_min_tab+tabString+"POSITION_INDEX:"+str(self.POSITION_INDEX))
        thisList.append(this_min_tab+tabString+"NORMAL_INDEX:"+str(self.NORMAL_INDEX))
        thisList.append(this_min_tab+tabString+"COLOR_INDEX:"+str(self.COLOR_INDEX))

        component_index = 0
        component_offset = 0

        while component_index < len(self.vertex_format):
            vertex_format_component = self.vertex_format[component_index]
            component_name_bytestring, component_len, component_type = vertex_format_component
            component_name = component_name_bytestring.decode("utf-8")
            thisList.append(this_min_tab+tabString+component_name+".len:"+str(component_len))
            thisList.append(this_min_tab+tabString+component_name+".type:"+str(component_type))
            thisList.append(this_min_tab+tabString+component_name+".index:"+str(component_index))
            thisList.append(this_min_tab+tabString+component_name+".offset:"+str(component_offset))
            component_index += 1
            component_offset += component_len

        #thisList.append(this_min_tab+tabString+"POSITION_LEN:"+str(self.vertex_format[self.POSITION_INDEX][VFORMAT_VECTOR_LEN_INDEX]))

        if add_dump_comments_enable:
            #thisList.append(this_min_tab+tabString+"#VFORMAT_VECTOR_LEN_INDEX:"+str(VFORMAT_VECTOR_LEN_INDEX))
            thisList.append(this_min_tab+tabString+"#len(self.vertex_format):"+str(len(self.vertex_format)))
            thisList.append(this_min_tab+tabString+"#COLOR_OFFSET:"+str(self.COLOR_OFFSET))
            thisList.append(this_min_tab+tabString+"#len(self.vertex_format[self.COLOR_INDEX]):"+str(len(self.vertex_format[self.COLOR_INDEX])))
        channel_count = self.vertex_format[self.COLOR_INDEX][VFORMAT_VECTOR_LEN_INDEX]
        if add_dump_comments_enable:
            thisList.append(this_min_tab+tabString+"#vertex_bytes_per_pixel:"+str(channel_count))


        for k,v in sorted(self.properties.items()):
            thisList.append(this_min_tab+tabString+k+": "+v)

        thisTextureFileName=self.get_texture_diffuse_path()
        if thisTextureFileName is not None:
            thisList.append(this_min_tab+tabString+"get_texture_diffuse_path(): "+thisTextureFileName)

        #thisList=append_dump_as_yaml_array(thisList, "vertex_info_1D",self.vertices,this_min_tab+tabString)
        tabString="  "
        if add_dump_comments_enable:
            thisList.append(this_min_tab+tabString+"#1D vertex info array, aka:")
        thisList.append(this_min_tab+tabString+"vertices:")
        component_offset = 0
        vertex_actual_index = 0
        for i in range(0,len(self.vertices)):
            if add_dump_comments_enable:
                if component_offset==0:
                    thisList.append(this_min_tab+tabString+tabString+"#vertex ["+str(vertex_actual_index)+"]:")
                elif component_offset==self.COLOR_OFFSET:
                    thisList.append(this_min_tab+tabString+tabString+"#  color:")
                elif component_offset==self._NORMAL_OFFSET:
                    thisList.append(this_min_tab+tabString+tabString+"#  normal:")
                elif component_offset==self._POSITION_OFFSET:
                    thisList.append(this_min_tab+tabString+tabString+"#  position:")
                elif component_offset==self._TEXCOORD0_OFFSET:
                    thisList.append(this_min_tab+tabString+tabString+"#  texcoords0:")
                elif component_offset==self._TEXCOORD1_OFFSET:
                    thisList.append(this_min_tab+tabString+tabString+"#  texcoords1:")
            thisList.append(this_min_tab+tabString+tabString+"- "+str(self.vertices[i]))
            component_offset += 1
            if component_offset==self.vertex_depth:
                component_offset = 0
                vertex_actual_index += 1

        thisList.append(this_min_tab+tabString+"indices:")
        for i in range(0,len(self.indices)):
            thisList.append(this_min_tab+tabString+tabString+"- "+str(self.indices[i]))


    def on_vertex_format_change(self):
        self._POSITION_OFFSET = -1
        self._NORMAL_OFFSET = -1
        self._TEXCOORD0_OFFSET = -1
        self._TEXCOORD1_OFFSET = -1
        self.COLOR_OFFSET = -1

        self.POSITION_INDEX = -1
        self.NORMAL_INDEX = -1
        self.TEXCOORD0_INDEX = -1
        self.TEXCOORD1_INDEX = -1
        self.COLOR_INDEX = -1

        #this_pyglop.vertex_depth = 0
        offset = 0
        temp_vertex = list()
        for i in range(0,len(self.vertex_format)):
            #first convert from bytestring to str
            vformat_name_lower = str(self.vertex_format[i][VFORMAT_NAME_INDEX]).lower()
            if "pos" in vformat_name_lower:
                self._POSITION_OFFSET = offset
                self.POSITION_INDEX = i
            elif "normal" in vformat_name_lower:
                self._NORMAL_OFFSET = offset
                self.NORMAL_INDEX = i
            elif ("texcoord" in vformat_name_lower) or ("tc0" in vformat_name_lower):
                if self._TEXCOORD0_OFFSET<0:
                    self._TEXCOORD0_OFFSET = offset
                    self.TEXCOORD0_INDEX = i
                elif self._TEXCOORD1_OFFSET<0 and ("tc0" not in vformat_name_lower):
                    self._TEXCOORD1_OFFSET = offset
                    self.TEXCOORD1_INDEX = i
                #else ignore since is probably the second index such as a_texcoord1
            elif "color" in vformat_name_lower:
                self.COLOR_OFFSET = offset
                self.COLOR_INDEX = i
            offset += self.vertex_format[i][VFORMAT_VECTOR_LEN_INDEX]
        if offset > self.vertex_depth:
            print("ERROR: The count of values in vertex format chunks (chunk_count:"+str(len(self.vertex_format))+"; value_count:"+str(offset)+") is greater than the vertex depth "+str(self.vertex_depth))
        elif offset != self.vertex_depth:
            print("WARNING: The count of values in vertex format chunks (chunk_count:"+str(len(self.vertex_format))+"; value_count:"+str(offset)+") does not total to vertex depth "+str(self.vertex_depth))
        participle = "(before initializing)"



class PyGlopsMaterial:
    properties = None
    name = None
    mtlFileName = None  # mtl file path (only if based on WMaterial of WObject)

    #region vars based on OpenGL ES 1.1
    ambient_color = None  # vec4
    diffuse_color = None  # vec4
    specular_color = None  # vec4
    emissive_color = None  # vec4
    specular_exponent = None  # float
    #endregion vars based on OpenGL ES 1.1


    def __init__(self):
        self.properties = {}
        self.ambient_color = (0.0, 0.0, 0.0, 1.0)
        self.diffuse_color = (1.0, 1.0, 1.0, 1.0)
        self.specular_color = (1.0, 1.0, 1.0, 1.0)
        self.emissive_color = (0.0, 0.0, 0.0, 1.0)
        self.specular_exponent = 1.0

    def append_dump(self, thisList, this_min_tab):
        thisList.append(this_min_tab+"GlopsMaterial:")
        tabString="  "
        if self.name is not None:
            thisList.append(this_min_tab+tabString+"name: "+self.name)
        if self.mtlFileName is not None:
            thisList.append(this_min_tab+tabString+"mtlFileName: "+self.mtlFileName)
        for k,v in sorted(self.properties.items()):
            thisList.append(this_min_tab+tabString+k+": "+str(v))

#variable name ends in xyz so must be ready to be swizzled
def angles_to_angle_and_matrix(angles_list_xyz):
    result_angle_matrix = [0.0, 0.0, 0.0, 0.0]
    for axisIndex in range(len(angles_list_xyz)):
        while angles_list_xyz[axisIndex]<0:
            angles_list_xyz[axisIndex] += 360.0
        if angles_list_xyz[axisIndex] > result_angle_matrix[0]:
            result_angle_matrix[0] = angles_list_xyz[axisIndex]
    if result_angle_matrix[0] > 0:
        for axisIndex in range(len(angles_list_xyz)):
            result_angle_matrix[1+axisIndex] = angles_list_xyz[axisIndex] / result_angle_matrix[0]
    else:
        result_angle_matrix[3] = .000001
    return result_angle_matrix


def theta_radians_from_rectangular(x, y):
    theta = 0.0
    if (y != 0.0) or (x != 0.0):
        # if x == 0:
        #     if y < 0:
        #         theta = math.radians(-90)
        #     elif y > 0:
        #         theta = math.radians(90.0)
        # elif y == 0:
        #     if x < 0:
        #         theta = math.radians(180.0)
        #     elif x > 0:
        #         theta = math.radians(0.0)
        # else:
        #     theta = math.atan(y/x)
        theta = math.atan2(y, x)
    return theta


#Also in wobjfile.py:
def append_dump_as_yaml_array(thisList, thisName, sourceList, this_min_tab):
    tabString="  "
    thisList.append(this_min_tab+thisName+":")
    for i in range(0,len(sourceList)):
        thisList.append(this_min_tab+tabString+"- "+str(sourceList[i]))


def new_tuple(length, fill_start=0, fill_len=-1, fill_value=1.0):
    result = None
    tmp=list()
    fill_count = 0
    for i in range(0,length):
        if i>=fill_start and fill_count<fill_len:
            tmp.append(fill_value)
            fill_count += 1
        else:
            tmp.append(0.0)
    #if length==1:
        #result = tuple(0.0)
    #elif length==2:
        #result = (0.0, 0.0)
    #elif length==3:
        #result = (0.0, 0.0, 0.0)
    #elif length==4:
        #result = (0.0, 0.0, 0.0, 0.0)
    #elif length==5:
        #result = (0.0, 0.0, 0.0, 0.0, 0.0)
    #elif length==6:
        #result = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    #elif length==7:
        #result = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    #elif length==8:
        #result = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    return tuple(tmp)  # result


class PyGlopsLight:
    #region vars based on OpenGL ES 1.1
    position = None  # vec4 light position for a point/spot light or normalized dir. for a directional light
    ambient_color = None  # vec4
    diffuse_color = None  # vec4
    specular_color = None  # vec4
    spot_direction = None  # vec3
    attenuation_factors = None  # vec3
    spot_exponent = None  # float
    spot_cutoff_angle = None  # float
    compute_distance_attenuation = None  # bool
    #endregion vars based on OpenGL ES 1.1

    def __init__(self):
       self.position = (0.0, 0.0, 0.0, 0.0)
       self.ambient_color = (0.0, 0.0, 0.0, 0.0)
       self.diffuse_color = (0.0, 0.0, 0.0, 0.0)
       self.specular_color = (0.0, 0.0, 0.0, 0.0)
       self.spot_direction = (0.0, 0.0, 0.0)
       self.attenuation_factors = (0.0, 0.0, 0.0)
       self.spot_exponent = 1.0
       self.spot_cutoff_angle = 45.0
       self.compute_distance_attenuation = False


def get_glop_from_wobject(this_wobject):  #formerly set_from_wobject formerly import_wobject; based on _finalize_obj_data
    this_pyglop = None
    if (this_wobject.faces is not None):
        this_pyglop = self.new_glop()
        this_pyglop.source_path = this_wobject.source_path
        #from vertex_format above:
        #self.vertex_format = [
            #(b'a_position', , 'float'),  # Munshi prefers vec4 (Kivy prefers vec3)
            #(b'a_texcoord0', , 'float'),  # Munshi prefers vec4 (Kivy prefers vec2); vTexCoord0; available if enable_tex[0] is true
            #(b'a_texcoord1', , 'float'),  # Munshi prefers vec4 (Kivy prefers vec2);  available if enable_tex[1] is true
            #(b'a_color', 4, 'float'),  # vColor (diffuse color of vertex)
            #(b'a_normal', 3, 'float')  # vNormal; Munshi prefers vec3 (Kivy also prefers vec3)
            #]
        #self.on_vertex_format_change()
        IS_SELF_VFORMAT_OK = True
        if this_pyglop._POSITION_OFFSET<0:
            IS_SELF_VFORMAT_OK = False
            print("Couldn't find name containing 'pos' or 'position' in any vertex format element (see pyglops.py PyGlop constructor)")
        if this_pyglop._NORMAL_OFFSET<0:
            IS_SELF_VFORMAT_OK = False
            print("Couldn't find name containing 'normal' in any vertex format element (see pyglops.py PyGlop constructor)")
        if this_pyglop._TEXCOORD0_OFFSET<0:
            IS_SELF_VFORMAT_OK = False
            print("Couldn't find name containing 'texcoord' in any vertex format element (see pyglops.py PyGlop constructor)")
        if this_pyglop.COLOR_OFFSET<0:
            IS_SELF_VFORMAT_OK = False
            print("Couldn't find name containing 'color' in any vertex format element (see pyglops.py PyGlop constructor)")

        #vertices_offset = None
        #normals_offset = None
        #texcoords_offset = None
        #vertex_depth = 8
        #based on finish_object
    #         if this_pyglop._current_object == None:
    #             return
    #
        if not IS_SELF_VFORMAT_OK:
            sys.exit(1)
        zero_vertex = list()
        for index in range(0,this_pyglop.vertex_depth):
            zero_vertex.append(0.0)
        if (this_pyglop.vertex_format[this_pyglop.POSITION_INDEX][VFORMAT_VECTOR_LEN_INDEX]>3):
            zero_vertex[3] = 1.0
            #NOTE: this is done since usually if len is 3, simple.glsl included with kivy converts it to vec4 appending 1.0:
            #attribute vec3 v_pos;
            #void main (void) {
            #vec4(v_pos,1.0);
        #this_offset = this_pyglop.COLOR_OFFSET
        channel_count = this_pyglop.vertex_format[this_pyglop.COLOR_INDEX][VFORMAT_VECTOR_LEN_INDEX]
        for channel_subindex in range(0,channel_count):
            zero_vertex[this_pyglop.COLOR_OFFSET+channel_subindex] = -1.0  # -1.0 for None #TODO: asdf flag a different way (other than negative) to work with fake standard shader


        participle="accessing object from list"
        #this_wobject = this_pyglop.glops[index]
        this_pyglop.name = None
        this_name = ""
        try:
            if this_wobject.name is not None:
                this_pyglop.name = this_wobject.name
                this_name = this_wobject.name
        except:
            pass  #don't care

        try:
            #if this_wobject.wmaterial is None:
            participle="processing material"
            if this_wobject.wmaterial is not None:  # if this_wobject.properties["usemtl"] is not None:
                #this_wobject.material=this_pyglop._getMaterial(this_wobject.properties["usemtl"])
                if this_wobject.wmaterial._map_filename_dict is not None:  # if this_wobject.wmaterial is not None:
                    this_pyglop.set_textures_from_mtl_dict(this_wobject.wmaterial._map_filename_dict)
                    #TODO: so something with _map_params_dict (wobjfile.py makes each entry a list of params if OBJ had map params before map file name)
                else:
                    print("WARNING: this_wobject.wmaterial._map_filename_dict is None")
            else:
                print("WARNING: this_wobject.wmaterial is None")
        except:  # Exception as e:
            #print("Could not finish "+participle+" in get_glop_from_wobject: "+str(e))
            print("Could not finish "+participle+" in get_glop_from_wobject: ")
            view_traceback()

        if this_pyglop.vertices is None:
            this_pyglop.vertices = []
            vertex_components = zero_vertex[:]
            #obj format stores faces like (quads are allowed such as in following examples):
            #this_wobject_this_face 1399/1619 1373/1593 1376/1596 1400/1620
            #format is:
            #this_wobject_this_face VERTEX_I VERTEX_I VERTEX_I VERTEX_I
            #or
            #this_wobject_this_face VERTEX_I/TEXCOORDSINDEX VERTEX_I/TEXCOORDSINDEX VERTEX_I/TEXCOORDSINDEX VERTEX_I/TEXCOORDSINDEX
            #or
            #this_wobject_this_face VERTEX_I/TEXCOORDSINDEX/NORMALINDEX VERTEX_I/TEXCOORDSINDEX/NORMALINDEX VERTEX_I/TEXCOORDSINDEX/NORMALINDEX VERTEX_I/TEXCOORDSINDEX/NORMALINDEX
            #where *I are integers starting at 0 (stored starting at 1)
            #FACE_VERTEX_COMPONENT_VERTEX_INDEX = 0
            #FACE_VERTEX_COMPONENT_TEXCOORDS_INDEX = 1
            #FACE_VERTEX_COMPONENT_NORMAL_INDEX = 2
            #NOTE: in obj format, TEXCOORDS_INDEX is optional

            #FACE_VERTEX_COMPONENT_VERTEX_INDEX = 0
            #FACE_VERTEX_COMPONENT_TEXCOORDS_INDEX = 1
            #FACE_VERTEX_COMPONENT_NORMAL_INDEX = 2

            #nskrypnik put them in a different order than obj format (0,1,2) for some reason so do this order instead ONLY if using his obj loader:
            #FACE_VERTEX_COMPONENT_VERTEX_INDEX = 0
            #FACE_VERTEX_COMPONENT_TEXCOORDS_INDEX = 2
            #FACE_VERTEX_COMPONENT_NORMAL_INDEX = 1

            #use the following globals from wobjfile.py instead of assuming any FACE_VERTEX_COMPONENT values:
            #FACE_V  # index of vertex index in the face (since face is a list)
            #FACE_TC  # index of tc0 index in the face (since face is a list)
            #FACE_VN  # index of normal index in the face (since face is a list)

            source_face_index = 0
            try:
                if (len(this_pyglop.indices)<1):
                    participle = "before detecting vertex component offsets"
                    #detecting vertex component offsets is required since indices in an obj file are sometimes relative to the first index in the FILE not the object
                    if this_wobject.faces is not None:
                        #get offset
                        for faceIndex in range(0,len(this_wobject.faces)):
                            for componentIndex in range(0,len(this_wobject.faces[faceIndex])):
                                #print("found face "+str(faceIndex)+" component "+str(componentIndex)+": "+str(this_wobject.faces[faceIndex][componentIndex]))
                                #print(str(this_wobject.faces[faceIndex][vertexIndex]))
                                #if (len(this_wobject.faces[faceIndex][componentIndex])>=FACE_V):
                                #TODO: audit this code:
                                for vertexIndex in range(0,len(this_wobject.faces[faceIndex][componentIndex])):
                                    #calculate new offsets, in case obj file was botched (for correct obj format, wobjfile.py changes indices so they are relative to wobject ('o' command) instead of file
                                    if componentIndex==FACE_V:
                                        thisVertexIndex = this_wobject.faces[faceIndex][componentIndex][vertexIndex]
                                        #if vertices_offset is None or thisVertexIndex<vertices_offset:
                                            #vertices_offset = thisVertexIndex
                                    #if (len(this_wobject.faces[faceIndex][componentIndex])>=FACE_TC):
                                    elif componentIndex==FACE_TC:
                                        thisTexCoordIndex = this_wobject.faces[faceIndex][componentIndex][vertexIndex]
                                        #if texcoords_offset is None or thisTexCoordIndex<texcoords_offset:
                                            #texcoords_offset = thisTexCoordIndex
                                    #if (len(this_wobject.faces[faceIndex][componentIndex])>=FACE_VN):
                                    elif componentIndex==FACE_VN:
                                        thisNormalIndex = this_wobject.faces[faceIndex][componentIndex][vertexIndex]
                                        #if normals_offset is None or thisNormalIndex<normals_offset:
                                            #normals_offset = thisNormalIndex

                        #if vertices_offset is not None:
                            #print("detected vertices_offset:"+str(vertices_offset))
                        #if texcoords_offset is not None:
                            #print("detected texcoords_offset:"+str(texcoords_offset))
                        #if normals_offset is not None:
                            #print("detected normals_offset:"+str(normals_offset))

                    participle = "before processing faces"
                    dest_vertex_index = 0
                    face_count = 0
                    new_texcoord = new_tuple(this_pyglop.vertex_format[this_pyglop.TEXCOORD0_INDEX][VFORMAT_VECTOR_LEN_INDEX])
                    if this_wobject.faces is not None:
                        for this_wobject_this_face in this_wobject.faces:
                            participle = "getting face components"
                            #print("face["+str(source_face_index)+"]: "+participle)

                            #DOES triangulate of more than 3 vertices in this face (connects each loose point to first vertex and previous vertex)
                            # (vertex_done_flags are no longer needed since that method is used)
                            #vertex_done_flags = list()
                            #for vertexinfo_index in range(0,len(this_wobject_this_face)):
                            #    vertex_done_flags.append(False)
                            #vertices_done_count = 0

                            #with wobjfile.py, each face is an arbitrary-length list of vertex_infos, where each vertex_info is a list containing vertex_index, texcoord_index, then normal_index, so ignore the following commented deprecated lines of code:
                            #verts =  this_wobject_this_face[0]
                            #norms = this_wobject_this_face[1]
                            #tcs = this_wobject_this_face[2]
                            #for vertexinfo_index in range(3):
                            vertexinfo_index = 0
                            source_face_vertex_count = 0
                            while vertexinfo_index<len(this_wobject_this_face):
                                #print("vertex["+str(vertexinfo_index)+"]")
                                vertex_info = this_wobject_this_face[vertexinfo_index]

                                vertex_index = vertex_info[FACE_V]
                                texcoord_index = vertex_info[FACE_TC]
                                normal_index = vertex_info[FACE_VN]

                                vertex = None
                                texcoord = None
                                normal = None


                                participle = "getting normal components"

                                #get normal components
                                normal = (0.0, 0.0, 1.0)
                                #if normals_offset is None:
                                #    normals_offset = 1
                                normals_offset = 0  # since wobjfile.py makes indices relative to object
                                try:
                                    #if (normal_index is not None) and (normals_offset is not None):
                                    #    participle = "getting normal components at "+str(normal_index-normals_offset)  # str(norms[face_index]-normals_offset)
                                    #else:
                                    participle = "getting normal components at "+str(normal_index)+"-"+str(normals_offset)  # str(norms[face_index]-normals_offset)
                                    if normal_index is not None:
                                        normal = this_wobject.normals[normal_index-normals_offset]
                                    #if norms[face_index] != -1:
                                        #normal = this_wobject.normals[norms[face_index]-normals_offset]
                                except:  # Exception as e:
                                    print("Could not finish "+participle+" for wobject named '"+this_name+"':")
                                    view_traceback()

                                participle = "getting texture coordinate components"
                                participle = "getting texture coordinate components at "+str(face_count)
                                participle = "getting texture coordinate components using index "+str(face_count)
                                #get texture coordinate components
                                #texcoord = (0.0, 0.0)
                                texcoord = new_texcoord[:]
                                #if texcoords_offset is None:
                                #    texcoords_offset = 1
                                texcoords_offset = 0  # since wobjfile.py makes indices relative to object
                                try:
                                    if this_wobject.texcoords is not None:
                                        #if (texcoord_index is not None) and (texcoords_offset is not None):
                                        #    participle = "getting texcoord components at "+str(texcoord_index-texcoords_offset)  # str(norms[face_index]-normals_offset)
                                        #else:
                                        participle = "getting texcoord components at "+str(texcoord_index)+"-"+str(texcoords_offset)  # str(norms[face_index]-normals_offset)

                                        if texcoord_index is not None:
                                            texcoord = this_wobject.texcoords[texcoord_index-texcoords_offset]
                                        #if tcs[face_index] != -1:
                                            #participle = "using texture coordinates at index "+str(tcs[face_index]-texcoords_offset)+" (after applying texcoords_offset:"+str(texcoords_offset)+"; Count:"+str(len(this_wobject.texcoords))+")"
                                            #texcoord = this_wobject.texcoords[tcs[face_index]-texcoords_offset]
                                    else:
                                        if verbose_enable:
                                            print("Warning: no texcoords found in wobject named '"+this_name+"'")
                                except:  # Exception as e:
                                    print("Could not finish "+participle+" for wobject named '"+this_name+"':")
                                    view_traceback()

                                participle = "getting vertex components"
                                #if vertices_offset is None:
                                #    vertices_offset = 1
                                vertices_offset = 0  # since wobjfile.py makes indices relative to object
                                #participle = "accessing face vertex "+str(verts[face_index]-vertices_offset)+" (after applying vertices_offset:"+str(vertices_offset)+"; Count:"+str(len(this_wobject.vertices))+")"
                                participle = "accessing face vertex "+str(vertex_index)+"-"+str(vertices_offset)+" (after applying vertices_offset:"+str(vertices_offset)
                                if (this_wobject.vertices is not None):
                                    participle += "; Count:"+str(len(this_wobject.vertices))+")"
                                else:
                                    participle += "; this_wobject.vertices:None)"
                                try:
                                    #v = this_wobject.vertices[verts[face_index]-vertices_offset]
                                    v = this_wobject.vertices[vertex_index-vertices_offset]
                                except:  # Exception as e:
                                    print("Could not finish "+participle+" for wobject named '"+this_name+"':")
                                    view_traceback()

                                participle = "combining components"
                                #vertex_components = [v[0], v[1], v[2], normal[0], normal[1], normal[2], texcoord[0], 1 - texcoord[1]] #TODO: why does kivy-rotation3d version have texcoord[1] instead of 1 - texcoord[1]
                                vertex_components = list()
                                for i in range(0,this_pyglop.vertex_depth):
                                    vertex_components.append(0.0)
                                for element_index in range(0,3):
                                    vertex_components[this_pyglop._POSITION_OFFSET+element_index] = v[element_index]
                                if (this_pyglop.vertex_format[this_pyglop.POSITION_INDEX][VFORMAT_VECTOR_LEN_INDEX]>3):
                                    vertex_components[this_pyglop._POSITION_OFFSET+3] = 1.0  # non-position padding value must be 1.0 for matrix math to work correctly
                                for element_index in range(0,3):
                                    vertex_components[this_pyglop._NORMAL_OFFSET+element_index] = normal[element_index]
                                for element_index in range(0,2):

                                    if element_index==1:
                                        vertex_components[this_pyglop._TEXCOORD0_OFFSET+element_index] = 1-texcoord[element_index]
                                    else:
                                        vertex_components[this_pyglop._TEXCOORD0_OFFSET+element_index] = texcoord[element_index]

                                if len(v)>3:
                                    #Handle nonstandard obj file with extended vertex info (color)
                                    abs_index = 0
                                    for element_index in range(4,len(v)):
                                        vertex_components[this_pyglop.COLOR_OFFSET+abs_index] = v[element_index]
                                        abs_index += 1
                                else:
                                    #default to white vertex color
                                    #TODO: asdf change this to black with alpha 0.0 and overlay (using material color as base)
                                    for element_index in range(0,4):
                                        vertex_components[this_pyglop.COLOR_OFFSET+element_index] = 1.0
                                this_pyglop.vertices.extend(vertex_components)
                                source_face_vertex_count += 1
                                vertexinfo_index += 1
                            #end while vertexinfo_index in face

                            participle = "combining triangle indices"
                            vertexinfo_index = 0
                            relative_source_face_vertex_index = 0  #required for tracking faces with less than 3 vertices
                            face_first_vertex_dest_index = dest_vertex_index
                            tesselated_f_count = 0
                            #example obj quad (without Texcoord) vertex_index/texcoord_index/normal_index:
                            #f 61//33 62//33 64//33 63//33
                            #face_vertex_list=list()  # in case verts are out of order, prevent tesselation from connecting wrong verts
                            while vertexinfo_index<len(this_wobject_this_face):
                                #face_vertex_list.append(dest_vertex_index)
                                if vertexinfo_index==2:
                                    #OK to assume dest vertices are in order, since just created them (should work even if source vertices are not in order)
                                    tri = [dest_vertex_index, dest_vertex_index+1, dest_vertex_index+2]
                                    this_pyglop.indices.extend(tri)
                                    dest_vertex_index += 3
                                    relative_source_face_vertex_index += 3
                                    tesselated_f_count += 1
                                elif vertexinfo_index>2:
                                    #TESSELATE MANUALLY for faces with more than 3 vertices (connect loose vertex with first vertex and previous vertex)
                                    tri = [face_first_vertex_dest_index, dest_vertex_index-1, dest_vertex_index]
                                    this_pyglop.indices.extend(tri)
                                    dest_vertex_index += 1
                                    relative_source_face_vertex_index += 1
                                    tesselated_f_count += 1
                                vertexinfo_index += 1

                            if (tesselated_f_count<1):
                                print("WARNING: Face tesselated to 0 faces")
                            elif (tesselated_f_count>1):
                                if verbose_enable:
                                    print("Face tesselated to "+str(tesselated_f_count)+" face(s)")

                            if relative_source_face_vertex_index<source_face_vertex_count:
                                print("WARNING: Face has fewer than 3 vertices (problematic obj file)")
                                dest_vertex_index += source_face_vertex_count - relative_source_face_vertex_index
                            source_face_index += 1
                    else:
                        print("WARNING: this_wobject.faces list is None in object '"+this_name+"'")
                    participle = "generating pivot point"

                    this_pyglop.transform_pivot_to_geometry()
                else:
                    print("ERROR: can't use pyglop since already has vertices (len(this_pyglop.indices)>=1)")

            except:  # Exception as e:
                #print("Could not finish "+participle+" at source_face_index "+str(source_face_index)+" in get_glop_from_wobject: "+str(e))
                print("Could not finish "+participle+" at source_face_index "+str(source_face_index)+" in get_glop_from_wobject: ")
                view_traceback()

                    #print("vertices after extending: "+str(this_wobject.vertices))
                    #print("indices after extending: "+str(this_wobject.indices))
        #         if this_wobject.mtl is not None:
        #             this_wobject.wmaterial = this_wobject.mtl.get(this_wobject.obj_material)
        #         if this_wobject.wmaterial is not None and this_wobject.wmaterial:
        #             this_wobject.set_textures_from_mtl_dict(this_wobject.wmaterial)
                #self.glops[self._current_object] = mesh
                #mesh.calculate_normals()
                #self.faces = []

        #         if (len(this_wobject.normals)<1):
        #             this_wobject.calculate_normals()  #this does not work. The call to calculate_normals is even commented out at <https://github.com/kivy/kivy/blob/master/examples/3Drendering/objloader.py> 20 Mar 2014. 16 Apr 2015.
        else:
            print("ERROR in get_glop_from_wobject: existing vertices found {this_pyglop.name:'"+str(this_name)+"'}")
    else:
        print("WARNING in get_glop_from_wobject: ignoring wobject where faces list is None.")
    return this_pyglop
#end def get_glop_from_wobject



class PyGlops:
    glops = None
    materials = None
    lastUntitledMeshNumber = -1
    lastCreatedMaterial = None
    lastCreatedMesh = None
    _walkmeshes = None
    ui = None
    camera_glop = None
    player_glop = None
    player_glop_index = None
    prev_inbounds_camera_translate = None
    _bumper_indices = None
    _bumpable_indices = None
    _world_min_y = None
    _world_grav_acceleration = None
    frames_per_second = None
    last_update_s = None
    _fly_enable = None
    _meshes = None  # this is a list of any implementation-specific type

    def __init__(self):
        self._fly_enable = False
        self._world_grav_acceleration = 9.8
        self.frames_per_second = 60.0
        self.camera_glop = self.new_glop()
        self.camera_glop.eye_height = 1.7  # 1.7 since 5'10" person is ~1.77m, and eye down a bit
        self.camera_glop.hit_radius = .2
        self.camera_glop.reach_radius = 2.5

        self.camera_glop.name = "camera_glop"
        self._walkmeshes = []
        self.glops = []
        self.materials = []
        self._bumper_indices = []
        self._bumpable_indices = []
    
    def _run_command(self, command, bumpable_index, bumper_index, bypass_handlers_enable=False):
        print("WARNING: _run_command should be implemented by a subclass since it requires using the graphics implementation") 
        return False
        
    def update(self):
        #print("coords:"+str(Window.mouse_pos))
        #see also asp and clip_top in init
        #screen_w_arc_theta = 32.0  # actual number is from proj matrix
        #screen_h_arc_theta = 18.0  # actual number is from proj matrix
        if self.env_rectangle is not None:
            if self.screen_w_arc_theta is not None and self.screen_h_arc_theta is not None:
                #region old way (does not repeat)
                #env_h_ratio = (2 * math.pi) / self.screen_h_arc_theta
                #env_w_ratio = env_h_ratio * math.pi
                #self.env_rectangle.size = (Window.size[0]*env_w_ratio,
                                           #Window.size[1]*env_h_ratio)
                #self.env_rectangle.pos = (-(self.camera_glop._rotate_instruction_y.angle/(2*math.pi)*self.env_rectangle.size[0]),
                                          #-(self.camera_glop._rotate_instruction_x.angle/(2*math.pi)*self.env_rectangle.size[1]))
                #engregion old way (does not repeat)
                self.env_rectangle.size = Window.size
                self.env_rectangle.pos = 0.0, 0.0
                view_right = self.screen_w_arc_theta / 2.0 + self.camera_glop._rotate_instruction_y.angle
                view_left = view_right - self.screen_w_arc_theta
                view_top = self.screen_h_arc_theta / 2.0 + self.camera_glop._rotate_instruction_x.angle + 90.0
                view_bottom = view_top - self.screen_h_arc_theta
                circle_theta = 2*math.pi
                view_right_ratio = view_right / circle_theta
                view_left_ratio = view_left / circle_theta
                view_top_ratio = view_top / circle_theta
                view_bottom_ratio = view_bottom / circle_theta
                #tex_coords order: u,      v,      u + w,  v,
                #                  u + w,  v + h,  u,      v + h
                # as per https://kivy.org/planet/2014/02/using-tex_coords-in-kivy-for-fun-and-profit/
                self.env_rectangle.tex_coords = view_left_ratio, view_bottom_ratio, view_right_ratio, view_bottom_ratio, \
                                                view_right_ratio, view_top_ratio, view_left_ratio, view_top_ratio



        x_rad, y_rad = self.get_view_angles_by_pos_rad(Window.mouse_pos)
        self.camera_glop._rotate_instruction_y.angle = x_rad
        self.camera_glop._rotate_instruction_x.angle = y_rad
        got_frame_delay = 0.0
        if self.last_update_s is not None:
            got_frame_delay = best_timer() - self.last_update_s
        self.last_update_s = best_timer()

        for i in range(0,len(self.glops)):
            if self.glops[i].look_target_glop is not None:
                self.glops[i].look_at(self.camera_glop)
                #print(str(self.glops[i].name)+" looks at "+str(self.glops[i].look_target_glop.name))
                #print("  at "+str((self.camera_glop._translate_instruction.x, self.camera_glop._translate_instruction.y, self.camera_glop._translate_instruction.z)))

        self.update_glops()
        
        rotation_multiplier_y = 0.0  # 1.0 is maximum speed
        moving_x = 0.0  # 1.0 is maximum speed
        moving_y = 0.0  # 1.0 is maximum speed
        moving_z = 0.0  # 1.0 is maximum speed; NOTE: increased z should move object closer to viewer in right-handed coordinate system
        moving_theta = 0.0
        position_change = [0.0, 0.0, 0.0]
        # for keycode strings, see  http://kivy.org/docs/_modules/kivy/core/window.html
        if self.player1_controller.get_pressed(Keyboard.keycodes["a"]):
            #if self.player1_controller.get_pressed(Keyboard.keycodes["shift"]):
            moving_x = 1.0
            #else:
            #    rotation_multiplier_y = -1.0
        if self.player1_controller.get_pressed(Keyboard.keycodes["d"]):
            #if self.player1_controller.get_pressed(Keyboard.keycodes["shift"]):
            moving_x = -1.0
            #else:
            #    rotation_multiplier_y = 1.0
        if self.player1_controller.get_pressed(Keyboard.keycodes["w"]):
            if self._fly_enable:
                #intentionally use z,y:
                moving_z, moving_y = get_rect_from_polar_rad(1.0, self.camera_glop._rotate_instruction_x.angle)
            else:
                moving_z = 1.0

        if self.player1_controller.get_pressed(Keyboard.keycodes["s"]):
            if self._fly_enable:
                #intentionally use z,y:
                moving_z, moving_y = get_rect_from_polar_rad(1.0, self.camera_glop._rotate_instruction_x.angle)
                moving_z *= -1.0
                moving_y *= -1.0
            else:
                moving_z = -1.0

        if self.player1_controller.get_pressed(Keyboard.keycodes["enter"]):
            self.use_selected(self.camera_glop)

        if rotation_multiplier_y != 0.0:
            delta_y = self.camera_turn_radians_per_frame * rotation_multiplier_y
            self.camera_glop._rotate_instruction_y.angle += delta_y
            #origin_distance = math.sqrt(self.camera_glop._translate_instruction.x*self.camera_glop._translate_instruction.x + self.camera_glop._translate_instruction.z*self.camera_glop._translate_instruction.z)
            #self.camera_glop._translate_instruction.x -= origin_distance * math.cos(delta_y)
            #self.camera_glop._translate_instruction.z -= origin_distance * math.sin(delta_y)

        #xz coords of edges of 16x16 square are:
        # move in the direction you are facing
        moving_theta = 0.0
        if moving_x != 0.0 or moving_y != 0.0 or moving_z != 0.0:
            #makes movement relative to rotation (which alaso limits speed when moving diagonally):
            moving_theta = theta_radians_from_rectangular(moving_x, moving_z)
            moving_r_multiplier = math.sqrt((moving_x*moving_x)+(moving_z*moving_z))
            if moving_r_multiplier > 1.0:
                moving_r_multiplier = 1.0  # Limited so that you can't move faster when moving diagonally


            #TODO: reprogram so adding math.radians(-90) is not needed (?)
            position_change[0] = self.camera_walk_units_per_frame*moving_r_multiplier * math.cos(self.camera_glop._rotate_instruction_y.angle+moving_theta+math.radians(-90))
            position_change[1] = self.camera_walk_units_per_frame*moving_y
            position_change[2] = self.camera_walk_units_per_frame*moving_r_multiplier * math.sin(self.camera_glop._rotate_instruction_y.angle+moving_theta+math.radians(-90))

            # if (self.camera_glop._translate_instruction.x + move_by_x > self._world_cube.get_max_x()):
            #     move_by_x = self._world_cube.get_max_x() - self.camera_glop._translate_instruction.x
            #     print(str(self.camera_glop._translate_instruction.x)+" of max_x:"+str(self._world_cube.get_max_x()))
            # if (self.camera_glop._translate_instruction.z + move_by_z > self._world_cube.get_max_z()):
            #     move_by_z = self._world_cube.get_max_z() - self.camera_glop._translate_instruction.z
            #     print(str(self.camera_glop._translate_instruction.z)+" of max_z:"+str(self._world_cube.get_max_z()))
            # if (self.camera_glop._translate_instruction.x + move_by_x < self._world_cube.get_min_x()):
            #     move_by_x = self._world_cube.get_min_x() - self.camera_glop._translate_instruction.x
            #     print(str(self.camera_glop._translate_instruction.x)+" of max_x:"+str(self._world_cube.get_max_x()))
            # if (self.camera_glop._translate_instruction.z + move_by_z < self._world_cube.get_min_z()):
            #     move_by_z = self._world_cube.get_min_z() - self.camera_glop._translate_instruction.z
            #     print(str(self.camera_glop._translate_instruction.z)+" of max_z:"+str(self._world_cube.get_max_z()))

            #print(str(self.camera_glop._translate_instruction.x)+","+str(self.camera_glop._translate_instruction.z)+" each coordinate should be between matching one in "+str(self._world_cube.get_min_x())+","+str(self._world_cube.get_min_z())+" and "+str(self._world_cube.get_max_x())+","+str(self._world_cube.get_max_z()))
            #print(str( (self.camera_glop._translate_instruction.x, self.camera_glop._translate_instruction.y, self.camera_glop._translate_instruction.z) )+" each coordinate should be between matching one in "+str(self.world_boundary_min)+" and "+str(self.world_boundary_max))

        #for axis_index in range(0,3):
        if position_change[0] is not None:
            self.camera_glop._translate_instruction.x += position_change[0]
        if position_change[1] is not None:
            self.camera_glop._translate_instruction.y += position_change[1]
        if position_change[2] is not None:
            self.camera_glop._translate_instruction.z += position_change[2]

        if len(self._walkmeshes)>0:
            walkmesh_result = self.get_container_walkmesh_and_poly_index_xz( (self.camera_glop._translate_instruction.x, self.camera_glop._translate_instruction.y, self.camera_glop._translate_instruction.z) )
            if walkmesh_result is None:
                #print("Out of bounds")
                corrected_pos = None
                #if self.prev_inbounds_camera_translate is not None:
                #    self.camera_glop._translate_instruction.x = self.prev_inbounds_camera_translate[0]
                #    self.camera_glop._translate_instruction.y = self.prev_inbounds_camera_translate[1]
                #    self.camera_glop._translate_instruction.z = self.prev_inbounds_camera_translate[2]
                #else:
                corrected_pos = self.get_nearest_walkmesh_vec3_using_xz( (self.camera_glop._translate_instruction.x, self.camera_glop._translate_instruction.y, self.camera_glop._translate_instruction.z) )
                if corrected_pos is not None:
                    pushed_angle = get_angle_between_two_vec3_xz( (self.camera_glop._translate_instruction.x, self.camera_glop._translate_instruction.y, self.camera_glop._translate_instruction.z), corrected_pos)
                    corrected_pos = get_pushed_vec3_xz_rad(corrected_pos, self.camera_glop.hit_radius, pushed_angle)
                    self.camera_glop._translate_instruction.x = corrected_pos[0]
                    self.camera_glop._translate_instruction.y = corrected_pos[1]   # TODO: check y (vertical) axis against eye height and jump height etc
                    #+ self.camera_glop.eye_height #no longer needed since swizzled to xz (get_nearest_walkmesh_vec3_using_xz returns original's y in return's y)
                    self.camera_glop._translate_instruction.z = corrected_pos[2]
                #else:
                #    print("ERROR: could not find point to bring player in bounds.")
            else:
                #print("In bounds")
                result_glop = self._walkmeshes[walkmesh_result["walkmesh_index"]]
                X_i = result_glop._POSITION_OFFSET + 0
                Y_i = result_glop._POSITION_OFFSET + 1
                Z_i = result_glop._POSITION_OFFSET + 2
                ground_tri = list()
                ground_tri.append( (result_glop.vertices[result_glop.indices[walkmesh_result["polygon_offset"]]*result_glop.vertex_depth+X_i], result_glop.vertices[result_glop.indices[walkmesh_result["polygon_offset"]]*result_glop.vertex_depth+Y_i], result_glop.vertices[result_glop.indices[walkmesh_result["polygon_offset"]]*result_glop.vertex_depth+Z_i]) )
                ground_tri.append( (result_glop.vertices[result_glop.indices[walkmesh_result["polygon_offset"]+1]*result_glop.vertex_depth+X_i], result_glop.vertices[result_glop.indices[walkmesh_result["polygon_offset"]+1]*result_glop.vertex_depth+Y_i], result_glop.vertices[result_glop.indices[walkmesh_result["polygon_offset"]+1]*result_glop.vertex_depth+Z_i]) )
                ground_tri.append( (result_glop.vertices[result_glop.indices[walkmesh_result["polygon_offset"]+2]*result_glop.vertex_depth+X_i], result_glop.vertices[result_glop.indices[walkmesh_result["polygon_offset"]+2]*result_glop.vertex_depth+Y_i], result_glop.vertices[result_glop.indices[walkmesh_result["polygon_offset"]+2]*result_glop.vertex_depth+Z_i]) )
                #self.camera_glop._translate_instruction.y = ground_tri[0][1] + self.camera_glop.eye_height
                ground_y = get_y_from_xz(ground_tri[0], ground_tri[1], ground_tri[2], self.camera_glop._translate_instruction.x, self.camera_glop._translate_instruction.z)
                self.camera_glop._translate_instruction.y = ground_y + self.camera_glop.eye_height
                if self._world_min_y is None or ground_y < self._world_min_y:
                    self._world_min_y = ground_y
                #if self.prev_inbounds_camera_translate is None or self.camera_glop._translate_instruction.y != self.prev_inbounds_camera_translate[1]:
                    #print("y:"+str(self.camera_glop._translate_instruction.y))
        else:
            #print("No bounds")
            pass
        self.prev_inbounds_camera_translate = self.camera_glop._translate_instruction.x, self.camera_glop._translate_instruction.y, self.camera_glop._translate_instruction.z

        # else:
        #     self.camera_glop._translate_instruction.x += self.camera_walk_units_per_frame * moving_x
        #     self.camera_glop._translate_instruction.z += self.camera_walk_units_per_frame * moving_z

        global missing_bumper_warning_enable
        global missing_bumpable_warning_enable
        global missing_radius_warning_enable
        for bumper_index_index in range(0,len(self._bumper_indices)):
            bumper_index = self._bumper_indices[bumper_index_index]
            if self.glops[bumper_index].actor_dict is not None and \
               "ai_enable" in self.glops[bumper_index].actor_dict and \
               self.glops[bumper_index].actor_dict["ai_enable"]:
                self.process_ai(bumper_index)
                if self.glops[bumper_index].actor_dict["target_index"] is not None:
                    self.glops[bumper_index].actor_dict["target_pos"] = get_vec3_from_point(self.glops[self.glops[bumper_index].actor_dict["target_index"]]._translate_instruction)
                elif self.glops[bumper_index].actor_dict["moveto_index"] is not None:
                    if not self.glops[self.glops[bumper_index].actor_dict["moveto_index"]].visible_enable:
                        self.glops[bumper_index].actor_dict["moveto_index"] = None
                    else:
                        self.glops[bumper_index].actor_dict["target_pos"] = get_vec3_from_point(self.glops[self.glops[bumper_index].actor_dict["moveto_index"]]._translate_instruction)
                if self.glops[bumper_index].actor_dict["target_pos"] is not None:
                    src_pos = get_vec3_from_point(self.glops[bumper_index]._translate_instruction)
                    dest_pos = self.glops[bumper_index].actor_dict["target_pos"]
                    r = self.glops[bumper_index].actor_dict["walk_units_per_second"] / self.frames_per_second
                    distance = get_distance_vec3_xz(src_pos, dest_pos)
                    if distance > self.glops[bumper_index].reach_radius:
                        theta = get_angle_between_two_vec3_xz(src_pos, dest_pos)
                        self.glops[bumper_index]._rotate_instruction_y.angle = theta
                        delta_x, delta_z = get_rect_from_polar_rad(r, theta)
                        self.glops[bumper_index]._translate_instruction.x += delta_x
                        self.glops[bumper_index]._translate_instruction.z += delta_z
            bumper_name = self.glops[bumper_index].name
            
        
        for bumpable_index_index in range(0, len(self._bumpable_indices)):

            bumpable_index = self._bumpable_indices[bumpable_index_index]
            bumpable_name = self.glops[bumpable_index].name
            bumpable_name = self.glops[bumpable_index]._temp_bumpable_enable = True
            if self.glops[bumpable_index].bump_enable is True:
                for bumper_index_index in range(0,len(self._bumper_indices)):
                    bumper_index = self._bumper_indices[bumper_index_index]
                    bumper_name = self.glops[bumper_index].name
                    distance = get_distance_kivyglops(self.glops[bumpable_index], self.glops[bumper_index])
                    if self.glops[bumpable_index].hit_radius is not None and self.glops[bumpable_index].hit_radius is not None:
                        total_hit_radius = 0.0
                        if self.glops[bumpable_index].projectile_dict is not None:
                            total_hit_radius = self.glops[bumpable_index].hit_radius+self.glops[bumper_index].hit_radius
                        else:
                            total_hit_radius = self.glops[bumpable_index].hit_radius+self.glops[bumper_index].reach_radius
                        if distance <= total_hit_radius:
                            #print("total_hit_radius:"+str(total_hit_radius))
                            if self.glops[bumpable_index].is_out_of_range:  # only run if ever moved away from it
                                if self.glops[bumper_index].bump_enable:
                                    if (self.glops[bumpable_index].projectile_dict is None) or (self.glops[bumper_index].hitbox is None) or self.glops[bumper_index].hitbox.contains_vec3(get_vec3_from_point(self.glops[bumpable_index]._translate_instruction)):
                                        #NOTE: already checked
                                        # bumpable_index bump_enable above
                                        #print("distance:"+str(total_hit_radius)+" <= total_hit_radius:"+str(total_hit_radius))
                                        if self.glops[bumpable_index].projectile_dict is None or ("owner" not in self.glops[bumpable_index].projectile_dict) or (self.glops[bumpable_index].projectile_dict["owner"] != self.glops[bumper_index].name):
                                            self._internal_bump_glop(bumpable_index, bumper_index)
                                        #else:
                                            #print("VERBOSE MESSAGE: cannot bump own projectile")
                                    else:
                                        global out_of_hitbox_note_enable
                                        if out_of_hitbox_note_enable:
                                            print("Bumped, but bumpable is not in bumper's hitbox: "+self.glops[bumper_index].hitbox.to_string())
                                            out_of_hitbox_note_enable = False
                            #else:
                                #print("not out of range yet")
                        else:
                            self.glops[bumpable_index].is_out_of_range = True
                            #print("did not bump "+str(bumpable_name)+" (bumper is at "+str( (self.camera_glop._translate_instruction.x,self.camera_glop._translate_instruction.y,self.camera_glop._translate_instruction.z) )+")")
                            pass
                    else:
                        if missing_radius_warning_enable:
                            print("WARNING: Missing radius while checking bumped named "+str(bumpable_name))
                            missing_radius_warning_enable = False
            if self.glops[bumpable_index]._cached_floor_y is None:
                self.glops[bumpable_index]._cached_floor_y = self._world_min_y
                #TODO: get from walkmesh instead
            if self.glops[bumpable_index].physics_enable:
                if self.glops[bumpable_index]._cached_floor_y is not None:
                    if self.glops[bumpable_index]._translate_instruction.y - self.glops[bumpable_index].hit_radius - kEpsilon > self.glops[bumpable_index]._cached_floor_y:
                        self.glops[bumpable_index]._translate_instruction.x += self.glops[bumpable_index].x_velocity
                        self.glops[bumpable_index]._translate_instruction.y += self.glops[bumpable_index].y_velocity
                        self.glops[bumpable_index]._translate_instruction.z += self.glops[bumpable_index].z_velocity
                        if got_frame_delay > 0.0:
                            #print("  GRAVITY AFFECTED:"+str(self.glops[bumpable_index]._translate_instruction.y)+" += "+str(self.glops[bumpable_index].y_velocity))
                            self.glops[bumpable_index].y_velocity -= self._world_grav_acceleration * got_frame_delay
                            #print("  THEN VELOCITY CHANGED TO:"+str(self.glops[bumpable_index].y_velocity))
                            #print("  FRAME INTERVAL:"+str(got_frame_delay))
                        else:
                            print("missing delay")
                    else:
                        #if self.glops[bumpable_index].z_velocity > kEpsilon:
                        if (self.glops[bumpable_index].y_velocity < 0.0 - (kEpsilon + self.glops[bumpable_index].hit_radius)):
                            #print("  HIT GROUND Y:"+str(self.glops[bumpable_index]._cached_floor_y))
                            if self.glops[bumpable_index].bump_sounds is not None and len(self.glops[bumpable_index].bump_sounds) > 0:
                                rand_i = random.randrange(0,len(self.glops[bumpable_index].bump_sounds))
                                self.play_sound(self.glops[bumpable_index].bump_sounds[rand_i])
                        if self.glops[bumpable_index].projectile_dict is not None:
                            if self.glops[bumpable_index].item_dict is not None and ("as_projectile" not in self.glops[bumpable_index].item_dict):
                                #save projectile settings before setting projectile_dict to to None:
                                self.glops[bumpable_index].item_dict["as_projectile"] = self.glops[bumpable_index].projectile_dict
                            if self.glops[bumpable_index].projectile_dict is not None:
                                self.glops[bumpable_index].projectile_dict = None
                        
                        self.glops[bumpable_index]._translate_instruction.y = self.glops[bumpable_index]._cached_floor_y + self.glops[bumpable_index].hit_radius
                        self.glops[bumpable_index].x_velocity = 0.0
                        self.glops[bumpable_index].y_velocity = 0.0
                        self.glops[bumpable_index].z_velocity = 0.0
                else:
                    #no gravity
                    self.glops[bumpable_index]._translate_instruction.x += self.glops[bumpable_index].x_velocity
                    self.glops[bumpable_index]._translate_instruction.y += self.glops[bumpable_index].y_velocity
                    self.glops[bumpable_index]._translate_instruction.z += self.glops[bumpable_index].z_velocity

    #end update        
        
   # This method overrides object bump code, and gives the item to the player (mimics "obtain" event)
    # cause player to obtain the item found first by keyword, then hide the item (overrides object bump code)
    def give_item_by_keyword_to_player_number(self, player_number, keyword, allow_owned_enable=False):
        indices = get_indices_of_similar_names(keyword, allow_owned_enable=allow_owned_enable)
        result = False
        if indices is not None and len(indices)>0:
            item_glop_index = indices[0]
            result = self.give_item_by_index_to_player_number(player_number, item_glop_index, "hide")
        return result

    # This method overrides object bump code, and gives the item to the player (mimics "obtain" command).
    # pre_commands can be either None (to imply default "hide") or a string containing semicolon-separated commands that will occur before obtain
    def give_item_by_index_to_player_number(self, player_number, item_glop_index, pre_commands=None, bypass_handlers_enable=True):
        result = False
        bumpable_index = item_glop_index
        bumper_index = self.get_player_glop_index(player_number)
        if verbose_enable:
            print("give_item_by_index_to_player_number; item_name:"+self.glops[bumpable_index]+"; player_name:"+self.glops[bumper_index].name+"")
        if pre_commands is None:
            pre_commands = "hide"  # default behavior is to hold item in inventory invisibly
        if pre_commands is not None:
            command_list = pre_commands.split(";")
            for command_original in command_list:
                command = command_original.strip()
                if command != "obtain":
                    self._run_command(command, bumpable_index, bumper_index, bypass_handlers_enable=bypass_handlers_enable)
                else:
                    print("  warning: skipped redundant 'obtain' command in post_commands param given to give_item_by_index_to_player_number")

        self._run_command("obtain", bumpable_index, bumper_index, bypass_handlers_enable=bypass_handlers_enable)
        result = True
        return result
        
    def _run_semicolon_separated_commands(self, semicolon_separated_commands, bumpable_index, bumper_index, bypass_handlers_enable=False):
        if semicolon_separated_commands is not None:
            command_list = semicolon_separated_commands.split(";")
            self._run_commands(command_list, bumpable_index, bumper_index, bypass_handlers_enable=bypass_handlers_enable)
    
    def _run_commands(self, command_list, bumpable_index, bumper_index, bypass_handlers_enable=False):
        for command_original in command_list:
            command = command_original.strip()
            self._run_command(command, bumpable_index, bumper_index, bypass_handlers_enable=bypass_handlers_enable)

    def _run_command(self, command, bumpable_index, bumper_index, bypass_handlers_enable=False):
        if command=="hide":
            self.hide_glop(self.glops[bumpable_index])
            self.glops[bumpable_index].bump_enable = False
        elif command=="obtain":
            #first, fire the (blank) overridable event handlers:
            self.obtain_glop(bumpable_name, bumper_name)
            self.obtain_glop_by_index(bumpable_index, bumper_index)
            #then manually transfer the glop to the player:
            self.glops[bumpable_index].item_dict["owner"] = self.glops[bumper_index].name
            item_event = self.glops[bumper_index].push_glop_item(self.glops[bumpable_index], bumpable_index)
            #process item event so selected inventory slot gets updated in case that is the found slot for the item:
            self.after_selected_item(item_event)
            if verbose_enable:
                print(command+" "+self.glops[bumpable_index].name)
        else:
            print("Glop named "+str(self.glops[bumpable_index].name)+" attempted an unknown glop command (in bump event): "+str(command))

    def hide_glop(self, this_glop):
        print("WARNING: hide_glop should be implemented by a sub-class since it is specific to graphics implementation")
        return False
        
    def show_glop(self, this_glop_index):
        print("WARNING: show_glop should be implemented by a sub-class since it is specific to graphics implementation")
        return False

    def after_selected_item(self, select_item_event_dict):
        name = None
        #proper_name = None
        inventory_index = None
        if select_item_event_dict is not None:
            calling_method_string = ""
            if "calling_method" in select_item_event_dict:
                calling_method_string = select_item_event_dict["calling_method"]
            if "name" in select_item_event_dict:
                name = select_item_event_dict["name"]
            else:
                print("ERROR in after_selected_item ("+calling_method_string+"): missing name in select_item_event_dict")
            #if "proper_name" in select_item_event_dict:
            #    proper_name = select_item_event_dict["proper_name"]
            #else:
            #    print("ERROR in after_selected_item ("+calling_method_string+"): missing proper_name in select_item_event_dict")
            if "inventory_index" in select_item_event_dict:
                inventory_index = select_item_event_dict["inventory_index"]
            else:
                print("ERROR in after_selected_item ("+calling_method_string+"): missing inventory_index in select_item_event_dict")
        self.use_button.text=str(inventory_index)+": "+str(name)

    def add_actor_weapon(self, glop_index, weapon_dict):
        result = False
        #item_event = self.player_glop.push_glop_item(self.glops[bumpable_index], bumpable_index)
        #process item event so selected inventory slot gets updated in case obtained item ends up in it:
        #self.after_selected_item(item_event)
        #if verbose_enable:
        #    print(command+" "+self.glops[bumpable_index].name)
        if "fired_sprite_path" in weapon_dict:
            indices = self.load_obj("meshes/sprite-square.obj")
            weapon_dict["fires_glops"] = list()
            if "name" not in weapon_dict or weapon_dict["name"] is None:
                weapon_dict["name"] = "Primary Weapon"
            if indices is not None:
                for i in range(0,len(indices)):
                    weapon_dict["fires_glops"].append(self.glops[indices[i]])
                    self.glops[indices[i]].set_texture_diffuse(weapon_dict["fired_sprite_path"])
                    self.glops[indices[i]].look_target_glop = self.camera_glop
                    item_event = self.player_glop.push_item(weapon_dict)
                    if (item_event is not None) and ("is_possible" in item_event) and (item_event["is_possible"]):
                        result = True
                        #process item event so selected inventory slot gets updated in case obtained item ends up in it:
                        self.after_selected_item(item_event)
                    #print("add_actor_weapon: using "+str(self.glops[indices[i]].name)+" as sprite.")
                for i in range(0,len(indices)):
                    self.hide_glop(self.glops[indices[i]])
            else:
                print("ERROR: got 0 objects from fired_sprite_path '"+str(weapon_dict["fired_sprite_path"]+"'"))
        #print("add_actor_weapon OK")
        return result

    def _internal_bump_glop(self, bumpable_index, bumper_index):
        bumpable_name = self.glops[bumpable_index].name
        bumper_name = self.glops[bumper_index].name
        #result =
        if self.ui is not None:
            self.ui.bump_glop(bumpable_name, bumper_name)
        #if result is not None:
            #if "bumpable_name" in result:
            #    bumpable_name = result["bumpable_name"]
            #if "bumper_name" in result:
            #    bumper_name = result["bumper_name"]
        #asdf remove if bumpable_glop.item_dict.

        #if bumpable_name is not None and bumper_name is not None:
        if self.glops[bumpable_index].item_dict is not None:
            if "bump" in self.glops[bumpable_index].item_dict:
                self.glops[bumpable_index].is_out_of_range = False  #prevents repeated bumping until out of range again
                if self.glops[bumpable_index].bump_enable:
                    if self.glops[bumpable_index].item_dict["bump"] is not None:
                        _run_semicolon_separated_commands(self.glops[bumpable_index].item_dict["bump"], bumpable_index, bumper_index);
                        commands = self.glops[bumpable_index].item_dict["bump"].split(";")
                        for command in commands:
                            command = command.strip()
                            print("  bump "+self.glops[bumpable_index].name+": "+command+" by "+self.glops[bumper_index].name)
                            self._run_command(command, bumpable_index, bumper_index)
                    else:
                        print("self.glops[bumpable_index].item_dict['bump'] is None")
            else:
                print("self.glops[bumpable_index].item_dict does not contain 'bump'")
        elif self.glops[bumpable_index].projectile_dict is not None:
            #print("  this_distance: "+str(distance))
            if self.glops[bumpable_index].projectile_dict is not None:
                self.attacked_glop(bumper_index, self.glops[bumpable_index].projectile_dict["owner_index"], self.glops[bumpable_index].projectile_dict)
                self.glops[bumpable_index].bump_enable = False
            else:
                pass
                #print("bumper:"+str( (self.glops[bumper_index]._translate_instruction.x, self.glops[bumper_index]._translate_instruction.y, self.glops[bumper_index]._translate_instruction.z) ) +
                #      "; bumped:"+str( (self.glops[bumpable_index]._translate_instruction.x, self.glops[bumpable_index]._translate_instruction.y, self.glops[bumpable_index]._translate_instruction.z) ))
            #if "bump" in self.glops[bumpable_index].item_dict:
            #NOTE ignore self.glops[bumpable_index].is_out_of_range
            # since firing at point blank range is ok.
            print("projectile bumped by object "+str(bumper_name))
            print("  hit_radius:"+str(self.glops[bumper_index].hit_radius))
            if self.glops[bumper_index].hitbox is not None:
                print("  hitbox: "+self.glops[bumper_index].hitbox.to_string())
            #else:
            #    print("self.glops[bumpable_index].item_dict does not contain 'bump'")
        else:
            print("bumped object '"+str(self.glops[bumpable_index].name)+"' is not an item")
    
    def get_player_glop_index(self, player_number):
        result = None
        if self.player_glop_index is not None:
            #TODO: check player_number instead
            result = self.player_glop_index
        else:
            if self.player_glop is not None:
                for i in range(0, len(self.glops)):
                    #TODO: check player_number instead
                    if self.glops[i] is self.player_glop:
                        result = i
                        print("WARNING: player_glop_index is not set," +
                            "but player_glop was found in glops")
                        break
        return result

    def append_dump(self, thisList):
        tabString="  "
        thisList.append("Glops:")
        for i in range(0,len(self.glops)):
            self.glops[i].append_dump(thisList, tabString)
        thisList.append("GlopsMaterials:")
        for i in range(0,len(self.materials)):
            self.materials[i].append_dump(thisList, tabString)

    def set_as_actor_by_index(self, index, template_dict):
        #result = False
        if index is not None:
            if index>=0:
                if index<len(self.glops):
                    actor_dict = get_dict_deepcopy(template_dict)
                    self.glops[index].actor_dict = actor_dict
                    if self.glops[index].hit_radius is None:
                        if "hit_radius" in actor_dict:
                            self.glops[index].hit_radius = actor_dict["hit_radius"]
                        else:
                            self.glops[index].hit_radius = .5
                    if "target_index" not in self.glops[index].actor_dict:
                        self.glops[index].actor_dict["target_index"] = None
                    if "moveto_index" not in self.glops[index].actor_dict:
                        self.glops[index].actor_dict["moveto_index"] = None
                    if "target_pos" not in self.glops[index].actor_dict:
                        self.glops[index].actor_dict["target_pos"] = None
                    if "walk_units_per_second" not in self.glops[index].actor_dict:
                        self.glops[index].actor_dict["walk_units_per_second"] = 1.0
                            
                    self.glops[index].calculate_hit_range()
                    self._bumper_indices.append(index)
                    self.glops[index].bump_enable = True
                    print("Set "+str(index)+" as bumper")
                    if self.glops[index].hitbox is None:
                        print("  hitbox: None")
                    else:
                        print("  hitbox: "+self.glops[index].hitbox.to_string())
                else:
                    print("ERROR in set_as_actor_by_index: index "+str(index)+" is out of range")
            else:
                print("ERROR in set_as_actor_by_index: index is "+str(index))
        else:
            print("ERROR in set_as_actor_by_index: index is None")
        #return result

    #always reimplement this so the camera is correct subclass 
    def new_glop(self):
        return PyGlop()

    def set_fly(self, fly_enable):
        if fly_enable==True:
            self._fly_enable = True
        else:
            self._fly_enable = False

    def create_material(self):
        return PyGlopsMaterial()

    def getMeshByName(self, name):
        result = None
        if name is not None:
            if len(self.glops)>0:
                for index in range(0,len(self.glops)):
                    if name==self.glops[index].name:
                        result=self.glops[index]
        return result

    def get_glop_list_from_obj(self, source_path):  # load_obj(self, source_path): #TODO: ? swapyz=False):
        participle = "(before initializing)"
        linePlus1 = 1
        #firstMeshIndex = len(self.glops)
        results = None
        try:
            #self.lastCreatedMesh = None
            participle = "checking path"
            if os.path.exists(source_path):
                results = list()  # create now, so that if None, that means source_path didn't exist
                participle = "setting up WObjFile"
                this_objfile = WObjFile()
                participle = "loading WObjFile"
                this_objfile.load(source_path)
                if this_objfile.wobjects is not None:
                    if len(this_objfile.wobjects)>0:
                        for i in range(0,len(this_objfile.wobjects)):
                            participle = "getting wobject"
                            this_wobject = this_objfile.wobjects[i]
                            participle = "converting wobject..."
                            this_pyglop = get_glop_from_wobject(this_wobject)
                            if this_pyglop is not None:
                                participle = "appending pyglop to scene"
                                #if results is None:
                                #    results = list()
                                results.append(this_pyglop)
                                if verbose_enable:
                                    if this_pyglop.name is not None:
                                        print("appended glop named '"+this_pyglop.name+"'")
                                    else:
                                        print("appended glop {name:None}")
                            else:
                                print("ERROR: this_pyglop is None after converting from wobject")
                    else:
                        print("ERROR: 0 wobjects could be read from '"+source_path+"'")
                else:
                    print("ERROR: 0 wobjects could be read from '"+source_path+"'")
            else:
                print("ERROR: file '"+str(source_path)+"' not found")
        except:  # Exception as e:
            #print("Could not finish a wobject in load_obj while "+participle+" on line "+str(linePlus1)+": "+str(e))
            print("Could not finish a wobject in load_obj while "+participle+" on line "+str(linePlus1)+":")
            view_traceback()
        return results

    def rotate_view_relative(self, angle, axis_index):
        #TODO: delete this method and see solutions from http://stackoverflow.com/questions/10048018/opengl-camera-rotation
        #such as set_view method of https://github.com/sgolodetz/hesperus2/blob/master/Shipwreck/MapEditor/GUI/Camera.java
        self.rotate_view_relative_around_point(angle, axis_index, self.camera_glop._translate_instruction.x, self.camera_glop._translate_instruction.y, self.camera_glop._translate_instruction.z)

    def rotate_view_relative_around_point(self, angle, axis_index, around_x, around_y, around_z):
        if axis_index == 0:  #x
            # += around_y * math.tan(angle)
            self.camera_glop._rotate_instruction_x.angle += angle
            # origin_distance = math.sqrt(around_z*around_z + around_y*around_y)
            # self.camera_glop._translate_instruction.z += origin_distance * math.cos(-1*angle)
            # self.camera_glop._translate_instruction.y += origin_distance * math.sin(-1*angle)
        elif axis_index == 1:  #y
            self.camera_glop._rotate_instruction_y.angle += angle
            # origin_distance = math.sqrt(around_x*around_x + around_z*around_z)
            # self.camera_glop._translate_instruction.x += origin_distance * math.cos(-1*angle)
            # self.camera_glop._translate_instruction.z += origin_distance * math.sin(-1*angle)
        else:  #z
            #self.camera_glop._translate_instruction.z += around_y * math.tan(angle)
            self.camera_glop._rotate_instruction_z.angle += angle
            # origin_distance = math.sqrt(around_x*around_x + around_y*around_y)
            # self.camera_glop._translate_instruction.x += origin_distance * math.cos(-1*angle)
            # self.camera_glop._translate_instruction.y += origin_distance * math.sin(-1*angle)

    def axis_index_to_string(self,index):
        result = "unknown axis"
        if (index==0):
            result = "x"
        elif (index==1):
            result = "y"
        elif (index==2):
            result = "z"
        return result

    def set_as_item(self, glop_name, template_dict):
        result = False
        if glop_name is not None:
            for i in range(0,len(self.glops)):
                if self.glops[i].name == glop_name:
                    return self.set_as_item_by_index(i, template_dict)
                    break

    def add_bump_sound_by_index(self, i, path):
        if path not in self.glops[i].bump_sounds:
            self.glops[i].bump_sounds.append(path)

    def set_as_item_by_index(self, i, template_dict):
        result = False
        item_dict = get_dict_deepcopy(template_dict)  #prevents every item template from being the one
        self.glops[i].item_dict = item_dict
        self.glops[i].item_dict["glop_name"] = self.glops[i].name
        self.glops[i].item_dict["glop_index"] = i
        self.glops[i].bump_enable = True
        self.glops[i].is_out_of_range = True  # allows item to be obtained instantly at start of main event loop
        self.glops[i].hit_radius = 0.1

        this_glop = self.glops[i]
        vertex_count = int(len(this_glop.vertices)/this_glop.vertex_depth)
        v_offset = 0
        min_y = None
        for v_number in range(0, vertex_count):
            if min_y is None or this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+1] < min_y:
                min_y = this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+1]
            v_offset += this_glop.vertex_depth
        if min_y is not None:
            self.glops[i].hit_radius = min_y
            if self.glops[i].hit_radius < 0.0:
                self.glops[i].hit_radius = 0.0 - self.glops[i].hit_radius
        else:
            print("ERROR: could not read any y values from glop named "+str(this_glop.name))
        #self.glops[i].hit_radius = 1.0
        self._bumpable_indices.append(i)
        return result

    def use_selected(self, user_glop):
        if user_glop is not None:
            if user_glop.properties is not None:
                if "inventory_items" in user_glop.properties:
                    if "inventory_index" in user_glop.properties:
                        try:
                            if user_glop.properties["inventory_index"] > -1:
                                user_glop.properties["inventory_items"][user_glop.properties["inventory_index"]]
                                this_item = user_glop.properties["inventory_items"][user_glop.properties["inventory_index"]]
                                glop_index = None
                                item_glop = None
                                if "glop_index" in this_item:
                                    glop_index = this_item["glop_index"]
                                    if glop_index is not None:
                                        item_glop = self.glops[glop_index]
                                if item_glop is not None:
                                    if item_glop.item_dict is not None:
                                        if "use" in item_glop.item_dict:
                                            is_ready = True
                                            if "cooldown" in item_glop.item_dict:
                                                is_ready = False
                                                if ("RUNTIME_last_used_time" not in item_glop.item_dict) or (time.time() - item_glop.item_dict["RUNTIME_last_used_time"]):
                                                    if ("RUNTIME_last_used_time" in item_glop.item_dict):
                                                        is_ready = True
                                                    #else Don't assume cooled down when obtained, otherwise rapid firing items will be allowed
                                                    item_glop.item_dict["RUNTIME_last_used_time"] = time.time()
                                            if is_ready:
                                                if "use_sound" in item_glop.item_dict:
                                                    self.play_sound(item_glop.item_dict["use_sound"])
                                                print(item_glop.item_dict["use"]+" "+item_glop.name)
                                                if "throw_" in item_glop.item_dict["use"]:  # such as item_dict["throw_arc"]
                                                    if "as_projectile" in item_glop.item_dict:
                                                        item_glop.projectile_dict = item_glop.item_dict["as_projectile"]
                                                        item_glop.projectile_dict["owner"] = user_glop.name
                                                        item_glop.projectile_dict["owner_index"] = user_glop.index
                                                    if "owner" in item_glop.item_dict:
                                                        del item_glop.item_dict["owner"]  # ok since still in projectile_dict if matters
                                                    #or useless_string = my_dict.pop('key', None)  # where None causes to return None instead of throwing KeyError if not found
                                                    self.glops[item_glop.item_dict["glop_index"]].physics_enable = True
                                                    throw_speed = 1.0 # meters/sec
                                                    try:
                                                        x_angle = user_glop._rotate_instruction_x.angle + math.radians(30)
                                                        if x_angle > math.radians(90):
                                                            x_angle = math.radians(90)
                                                        self.glops[item_glop.item_dict["glop_index"]].y_velocity = throw_speed * math.sin(x_angle)
                                                        horizontal_throw_speed = throw_speed * math.cos(x_angle)
                                                        self.glops[item_glop.item_dict["glop_index"]].x_velocity = horizontal_throw_speed * math.cos(user_glop._rotate_instruction_y.angle)
                                                        self.glops[item_glop.item_dict["glop_index"]].z_velocity = horizontal_throw_speed * math.sin(user_glop._rotate_instruction_y.angle)

                                                    except:
                                                        self.glops[item_glop.item_dict["glop_index"]].x_velocity = 0
                                                        self.glops[item_glop.item_dict["glop_index"]].z_velocity = 0
                                                        print("Could not finish getting throw x,,z values")
                                                        view_traceback()

                                                    self.glops[item_glop.item_dict["glop_index"]].is_out_of_range = False
                                                    self.glops[item_glop.item_dict["glop_index"]].bump_enable = True
                                                    event_dict = user_glop.pop_glop_item(user_glop.properties["inventory_index"])
                                                    self.after_selected_item(event_dict)
                                                    item_glop.visible_enable = True
                                                    item_glop._translate_instruction.x = user_glop._translate_instruction.x
                                                    item_glop._translate_instruction.y = user_glop._translate_instruction.y
                                                    item_glop._translate_instruction.z = user_glop._translate_instruction.z
                                                    self._meshes.add(item_glop.get_context())  # TODO: show_glop instead for consistency? how was it hidden?
                                        else:
                                            print(item_glop.name+" has no use.")
                                    else:
                                        print("ERROR: tried to use a glop that is not an item (this should not be in "+str(user_glop.name)+"'s inventory)")
                                elif "fire_type" in this_item:
                                    if this_item["fire_type"] != "throw_linear":
                                        print("WARNING: "+this_item["fire_type"]+" not implemented, so using throw_linear")
                                    weapon_dict = this_item
                                    favorite_pivot = None
                                    for fires_glop in weapon_dict["fires_glops"]:
                                        if "subscript" not in weapon_dict:
                                            weapon_dict["subscript"] = 0
                                        fired_glop = fires_glop.copy_as_mesh_instance()
                                        fired_glop.bump_enable = True
                                        fired_glop.projectile_dict = get_dict_deepcopy(weapon_dict)
                                        fired_glop.projectile_dict["owner"] = user_glop.name
                                        fired_glop.projectile_dict["owner_index"] = user_glop.index
                                        if favorite_pivot is None:
                                            #favorite_pivot = [0.0, 0.0, 0.0]
                                            favorite_pivot = (fired_glop._translate_instruction.x, fired_glop._translate_instruction.y, fired_glop._translate_instruction.z)
                                        fired_glop._translate_instruction.x += fired_glop._translate_instruction.x - favorite_pivot[0]
                                        fired_glop._translate_instruction.y += fired_glop._translate_instruction.y - favorite_pivot[1]
                                        fired_glop._translate_instruction.z += fired_glop._translate_instruction.z - favorite_pivot[2]
                                        fired_glop._translate_instruction.x = user_glop._translate_instruction.x
                                        fired_glop._translate_instruction.y = user_glop._translate_instruction.y
                                        fired_glop._translate_instruction.z = user_glop._translate_instruction.z
                                        fired_glop.name = fires_glop.name + "." + str(weapon_dict["subscript"])
                                        projectile_speed = 1.0
                                        if "projectile_speed" in weapon_dict:
                                            projectile_speed = weapon_dict["projectile_speed"]
                                        x_off, z_off = get_rect_from_polar_rad(projectile_speed, user_glop._rotate_instruction_y.angle)
                                        fired_glop.x_velocity = x_off
                                        fired_glop.z_velocity = z_off
                                        x_off, y_off = get_rect_from_polar_rad(projectile_speed, user_glop._rotate_instruction_x.angle)
                                        fired_glop.y_velocity = y_off
                                        #print("projectile velocity x,y,z:"+str((fired_glop.x_velocity, fired_glop.y_velocity, fired_glop.z_velocity)))
                                        fired_glop.visible_enable = True
                                        self.glops.append(fired_glop)
                                        fired_glop.physics_enable = True
                                        fired_glop.bump_enable = True
                                        self._meshes.add(fired_glop.get_context())  # _meshes is a visible instruction group
                                        weapon_dict["subscript"] += 1
                                        self._bumpable_indices.append(len(self.glops)-1)
                                        #start off a ways away:
                                        fired_glop._translate_instruction.x += fired_glop.x_velocity*2
                                        fired_glop._translate_instruction.y += fired_glop.y_velocity*2
                                        fired_glop._translate_instruction.z += fired_glop.z_velocity*2
                                        fired_glop._translate_instruction.y -= user_glop.eye_height/2

                        except:
                            print("user_glop.name:"+str(user_glop.name))
                            print('user_glop.properties["inventory_index"]:'+str(user_glop.properties["inventory_index"]))
                            print('len(user_glop.properties["inventory_items"]):'+str(len(user_glop.properties["inventory_items"])))
                            print("Could not finish use_selected:")
                            view_traceback()


    def load_glops(self):
        print("WARNING: subclass of KivyGlopsWindow should implement load_glops (and usually update_glops which will be called before each frame is drawn)")

    def update_glops(self):
        # subclass of KivyGlopsWindow can implement load_glops
        pass

    #def get_player_glop_index(self, player_number):
    #    result = self.get_player_glop_index(self, player_number)

    def killed_glop(self, index, weapon_dict):
        print("subclass should implement killed_glop" + \
            " (allowing variables other than pos to be None)")

    def kill_glop_by_index(self, index, weapon_dict=None):
        self.killed_glop(index, weapon_dict)
        self.hide_glop(self.glops[index])
        self.glops[index].bump_enable = False
        
    def bump_glop(self, bumpable_name, bumper_name):
        return None

    def attacked_glop(self, attacked_index, attacker_index, weapon_dict):
        print("attacked_glop should be implemented by the subclass" + \
            "which would know how to damage or calculate defense" + \
            "or other properties")
        #trivial example:
        #self.glops[attacked_index].actor_dict["hp"] -= weapon_dict["hit_damage"]
        #if self.glops[attacked_index].actor_dict["hp"] <= 0:
        #    self.explode_glop_by_index(attacked_index)
        return None

    def obtain_glop(self, bumpable_name, bumper_name):
        return None

    def obtain_glop_by_index(self, bumpable_index, bumper_index):
        return None

    def get_nearest_walkmesh_vec3_using_xz(self, pt):
        result = None
        closest_distance = None
        poly_sides_count = 3
        #corners = list()
        #for i in range(0,poly_sides_count):
        #    corners.append( (0.0, 0.0, 0.0) )
        for this_glop in self._walkmeshes:
            face_i = 0
            indices_count = len(this_glop.indices)
            while (face_i<indices_count):
                v_offset = this_glop.indices[face_i]*this_glop.vertex_depth
                a_vertex = this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+0], this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+1], this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+2]
                v_offset = this_glop.indices[face_i+1]*this_glop.vertex_depth
                b_vertex = this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+0], this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+1], this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+2]
                v_offset = this_glop.indices[face_i+2]*this_glop.vertex_depth
                c_vertex = this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+0], this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+1], this_glop.vertices[v_offset+this_glop._POSITION_OFFSET+2]
                #side_a_distance = get_distance_vec3_xz(pt, a_vertex, b_vertex)
                #side_b_distance = get_distance_vec3_xz(pt, b_vertex, c_vertex)
                #side_c_distance = get_distance_vec3_xz(pt, c_vertex, a_vertex)
                this_point = get_nearest_vec3_on_vec3line_using_xz(pt, a_vertex, b_vertex)
                this_distance = this_point[3] #4th index of returned tuple is distance
                tri_distance = this_distance
                tri_point = this_point

                this_point = get_nearest_vec3_on_vec3line_using_xz(pt, b_vertex, c_vertex)
                this_distance = this_point[3] #4th index of returned tuple is distance
                if this_distance < tri_distance:
                    tri_distance = this_distance
                    tri_point = this_point

                this_point = get_nearest_vec3_on_vec3line_using_xz(pt, c_vertex, a_vertex)
                this_distance = this_point[3] #4th index of returned tuple is distance
                if this_distance < tri_distance:
                    tri_distance = this_distance
                    tri_point = this_point

                if (closest_distance is None) or (tri_distance<closest_distance):
                    result = tri_point[0], tri_point[1], tri_point[2]  # ok to return y since already swizzled (get_nearest_vec3_on_vec3line_using_xz copies source's y to return's y)
                    closest_distance = tri_distance
                face_i += poly_sides_count
        return result

    def get_nearest_walkmesh_vertex_using_xz(self, pt):
        result = None
        second_nearest_pt = None
        for this_glop in self._walkmeshes:
            X_i = this_glop._POSITION_OFFSET + 0
            Y_i = this_glop._POSITION_OFFSET + 1
            Z_i = this_glop._POSITION_OFFSET + 2
            X_abs_i = X_i
            Y_abs_i = Y_i
            Z_abs_i = Z_i
            v_len = len(this_glop.vertices)
            distance_min = None
            while X_abs_i < v_len:
                distance = math.sqrt( (pt[0]-this_glop.vertices[X_abs_i+0])**2 + (pt[2]-this_glop.vertices[X_abs_i+2])**2 )
                if (result is None) or (distance_min) is None or (distance<distance_min):
                    #if result is not None:
                        #second_nearest_pt = result[0],result[1],result[2]
                    result = this_glop.vertices[X_abs_i+0], this_glop.vertices[X_abs_i+1], this_glop.vertices[X_abs_i+2]
                    distance_min = distance
                X_abs_i += this_glop.vertex_depth

            #DOESN'T WORK since second_nearest_pt may not be on edge
            #if second_nearest_pt is not None:
            #    distance1 = get_distance_vec3_xz(pt, result)
            #    distance2 = get_distance_vec3_xz(pt, second_nearest_pt)
            #    distance_total=distance1+distance2
            #    distance1_weight = distance1/distance_total
            #    distance2_weight = distance2/distance_total
            #    result = result[0]*distance1_weight+second_nearest_pt[0]*distance2_weight, result[1]*distance1_weight+second_nearest_pt[1]*distance2_weight, result[2]*distance1_weight+second_nearest_pt[2]*distance2_weight
                #TODO: use second_nearest_pt to get nearest location along the edge instead of warping to a vertex
        return result

    def is_in_any_walkmesh_xz(self, check_vec3):
        return get_container_walkmesh_and_poly_index_xz(check_vec3) is not None

    def get_container_walkmesh_and_poly_index_xz(self, check_vec3):
        result = None
        X_i = 0
        second_i = 2  # actually z since ignoring y
        check_vec2 = check_vec3[X_i], check_vec3[second_i]
        walkmesh_i = 0
        while walkmesh_i < len(self._walkmeshes):
            this_glop = self._walkmeshes[walkmesh_i]
            X_i = this_glop._POSITION_OFFSET + 0
            second_i = this_glop._POSITION_OFFSET + 2
            poly_side_count = 3
            poly_count = int(len(this_glop.indices)/poly_side_count)
            poly_offset = 0
            for poly_index in range(0,poly_count):
                if (  is_in_triangle_vec2( check_vec2, (this_glop.vertices[this_glop.indices[poly_offset]*this_glop.vertex_depth+X_i],this_glop.vertices[this_glop.indices[poly_offset]*this_glop.vertex_depth+second_i]), (this_glop.vertices[this_glop.indices[poly_offset+1]*this_glop.vertex_depth+X_i],this_glop.vertices[this_glop.indices[poly_offset+1]*this_glop.vertex_depth+second_i]), (this_glop.vertices[this_glop.indices[poly_offset+2]*this_glop.vertex_depth+X_i],this_glop.vertices[this_glop.indices[poly_offset+2]*this_glop.vertex_depth+second_i]) )  ):
                    result = dict()
                    result["walkmesh_index"] = walkmesh_i
                    result["polygon_offset"] = poly_offset
                    break
                poly_offset += poly_side_count
            walkmesh_i += 1
        return result

    def use_walkmesh(self, name, hide=True):
        result = False
        #for this_glop in self.glops:
        for index in range(0, len(self.glops)):
            if self.glops[index].name == name:
                result = True
                if self.glops[index] not in self._walkmeshes:
                    self._walkmeshes.append(self.glops[index])
                    print("Applying walkmesh translate "+translate_to_string(self.glops[index]._translate_instruction))
                    self.glops[index].apply_translate()
                    print("  pivot:"+str(self.glops[index]._pivot_point))
                    if hide:
                        self.hide_glop(self.glops[index])
                break
        return result

    def get_similar_names(self, partial_name):
        results = None
        checked_count = 0
        if partial_name is not None and len(partial_name)>0:
            partial_name_lower = partial_name.lower()
            results = list()
            for this_glop in self.glops:
                checked_count += 1
                #print("checked "+this_glop.name.lower())
                if this_glop.name is not None:
                    if partial_name_lower in this_glop.name.lower():
                        results.append(this_glop.name)
        #print("checked "+str(checked_count))
        return results

    def get_indices_by_source_path(self, source_path):
        results = None
        checked_count = 0
        if source_path is not None and len(source_path)>0:
            results = list()
            for index in range(0,len(self.glops)):
                this_glop = self.glops[index]
                checked_count += 1
                #print("checked "+this_glop.name.lower())
                if this_glop.source_path is not None:
                    if source_path == this_glop.source_path:
                        results.append(index)
        #print("checked "+str(checked_count))
        return results


    def get_indices_of_similar_names(self, partial_name, allow_owned_enable=True):
        results = None
        checked_count = 0
        if partial_name is not None and len(partial_name)>0:
            partial_name_lower = partial_name.lower()
            results = list()
            for index in range(0,len(self.glops)):
                this_glop = self.glops[index]
                checked_count += 1
                #print("checked "+this_glop.name.lower())
                if this_glop.name is not None and \
                   ( allow_owned_enable or \
                     this_glop.item_dict is None or \
                     "owner" not in this_glop.item_dict ):
                    if partial_name_lower in this_glop.name.lower():
                        results.append(index)
        #print("checked "+str(checked_count))
        return results

    #Find list of similar names slightly faster than multiple calls
    # to get_indices_of_similar_names: the more matches earlier in
    # the given partial_names array, the faster this method returns
    # (therefore overlapping sets are sacrificed).
    #Returns: list that is always the length of partial_names + 1,
    # as each item is a list of indicies where name contains the
    # corresponding partial name, except last index which is all others.
    def get_index_lists_by_similar_names(self, partial_names, allow_owned_enable=True):
        results = None
        checked_count = 0
        if len(partial_names)>0:
            results_len = len(partial_names)
            results = [list() for i in range(results_len + 1)]
            for index in range(0,len(self.glops)):
                this_glop = self.glops[index]
                checked_count += 1
                #print("checked "+this_glop.name.lower())
                match_indices = list(results_len)
                match = False
                for i in range(0, results_len):
                    partial_name_lower = partial_names[i].lower()
                    if this_glop.name is not None and \
                       ( allow_owned_enable or \
                         this_glop.item_dict is None or \
                         "owner" not in this_glop.item_dict ):
                        if partial_name_lower in this_glop.name.lower():
                            results[i].append(index)
                            match = True
                            break
                if not match:
                    results[results_len].append(index)
        #print("checked "+str(checked_count))
        return results


    def set_world_boundary_by_object(self, thisGlopsMesh, use_x, use_y, use_z):
        self._world_cube = thisGlopsMesh
        if (self._world_cube is not None):
            self.world_boundary_min = [self._world_cube.get_min_x(), None, self._world_cube.get_min_z()]
            self.world_boundary_max = [self._world_cube.get_max_x(), None, self._world_cube.get_max_z()]

            for axis_index in range(0,3):
                if self.world_boundary_min[axis_index] is not None:
                    self.world_boundary_min[axis_index] += self.projection_near + 0.1
                if self.world_boundary_max[axis_index] is not None:
                    self.world_boundary_max[axis_index] -= self.projection_near + 0.1
        else:
            self.world_boundary_min = [None,None,None]
            self.world_boundary_max = [None,None,None]

    def get_view_angles_by_pos_rad(self, pos):
        global debug_dict
        x_angle = -math.pi + (float(pos[0])/float(self.width-1))*(2.0*math.pi)
        y_angle = -(math.pi/2.0) + (float(pos[1])/float(self.height-1))*(math.pi)
        if "View" not in debug_dict:
            debug_dict["View"] = dict()
        debug_dict["View"]["pos"] = str(pos)
        debug_dict["View"]["size"] = str( (self.width, self.height) )
        debug_dict["View"]["pitch,yaw"] = str((int(math.degrees(x_angle)),
                                                    int(math.degrees(y_angle))))
        if self.screen_w_arc_theta is not None and self.screen_h_arc_theta is not None:
            debug_dict["View"]["field of view"] = \
                str((int(math.degrees(self.screen_w_arc_theta)),
                     int(math.degrees(self.screen_h_arc_theta))))
        else:
            if "field of view" in debug_dict["View"]:
                debug_dict["View"]["field of view"] = None
        self.update_debug_label()
        return x_angle, y_angle

    def print_location(self):
        if verbose_enable:
            Logger.debug("self.camera_walk_units_per_second:"+str(self.camera_walk_units_per_second)+"; location:"+str( (self.camera_glop._translate_instruction.x, self.camera_glop._translate_instruction.y, self.camera_glop._translate_instruction.z) ))

    def get_pressed(self, key_name):
        return self.player1_controller.get_pressed(Keyboard.keycodes[key_name])

    def toggle_visual_debug(self):
        if not self._visual_debug_enable:
            self._visual_debug_enable = True
            self.debug_label.opacity = 1.0
        else:
            self._visual_debug_enable = False
            self.debug_label.opacity = 0.0

    def select_mesh_by_index(self, index):
        glops_count = len(self.glops)
        if (index>=glops_count):
            index=0
        if verbose_enable:
            Logger.debug("trying to select index "+str(index)+" (count is "+str(glops_count)+")...")
        if (glops_count > 0):
            self.selected_glop_index = index
            self.selected_glop = self.glops[index]
        else:
            self.selected_glop = None
            self.selected_glop_index = None
    
    def index_of_mesh(self, name):
        result = -1
        name_lower = name.lower()
        for i in range(0,len(self.glops)):
            source_name = None
            source_name_lower = None
            if self.glops[i].source_path is not None:
                source_name = os.path.basename(os.path.normpath(self.glops[i].source_path))
                source_name_lower = source_name.lower()
            if self.glops[i].name==name:
                result = i
                break
            elif self.glops[i].name.lower()==name_lower:
                print("WARNING: object with different capitalization was not considered a match: " + self.glops[i].name)
            elif (source_name_lower is not None) and (source_name_lower==name_lower
                  or os.path.splitext(source_name_lower)[0]==name_lower):
                result = i
                name_msg = "filename: '" + source_name + "'"
                if os.path.splitext(source_name_lower)[0]==name_lower:
                    name_msg = "part of filename: '" + os.path.splitext(source_name)[0] + "'"
                print("WARNING: mesh was named '" + self.glops[i].name + "' but found using " + name_msg)
                if (i+1<len(self.glops)):
                    for j in range(i+1,len(self.glops)):
                        sub_source_name_lower = None
                        if self.glops[j].source_path is not None:
                            sub_source_name_lower = os.path.basename(os.path.normpath(self.glops[i].source_path)).lower()
                        if (source_name_lower is not None) and (source_name_lower==name_lower
                            or os.path.splitext(source_name_lower)[0]==name_lower):
                            print("  * could also be mesh named '" + self.glops[j].name+"'")
                break
        return result
    
    def select_mesh_by_name(self, name):
        found = False
        index = self.index_of_mesh(name)
        if index > -1:
            self.select_mesh_by_index(index)
            found = True
        return found
