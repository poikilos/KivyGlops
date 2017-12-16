"""
This module is the Kivy implementation of PyGlops.
It provides features that are specific to display method
(Kivy's OpenGL-like API in this case).
"""
from pyglops import *

from kivy.resources import resource_find
from kivy.graphics import *
from kivy.uix.widget import Widget
from kivy.core.image import Image
from pyrealtime import *
from kivy.clock import Clock

#stuff required for KivyGlopsWindow
from kivy.app import App
from kivy.core.window import Window
from kivy.core.window import Keyboard
from kivy.graphics.transformation import Matrix
from kivy.graphics.opengl import *
from kivy.graphics import *
#from kivy.input.providers.mouse import MouseMotionEvent
from kivy.factory import Factory
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle

from kivy.logger import Logger
from kivy.vector import Vector

from kivy.core.audio import SoundLoader

import timeit
from timeit import default_timer as best_timer


from common import *

import time
import random

#TODO: try adding captions and 2d axis indicators in canvas.after, or try RenderContext
sub_canvas_enable = False
missing_bumper_warning_enable = True
missing_bumpable_warning_enable = True
missing_radius_warning_enable = True
out_of_hitbox_note_enable = True

def get_distance_kivyglops(a_glop, b_glop):
    return math.sqrt((b_glop._translate_instruction.x - a_glop._translate_instruction.x)**2 +
                     (b_glop._translate_instruction.y - a_glop._translate_instruction.y)**2 +
                     (b_glop._translate_instruction.z - a_glop._translate_instruction.z)**2)

#def get_distance_vec3(a_vec3, b_vec3):
#    return math.sqrt((b_vec3[0] - a_vec3[0])**2 + (b_vec3[1] - a_vec3[1])**2 + (b_vec3[2] - a_vec3[2])**2)

def translate_to_string(_translate_instruction):
    result = "None"
    if _translate_instruction is not None:
        result = str([_translate_instruction.x, _translate_instruction.y, _translate_instruction.z])
    return result


class KivyGlopsMaterial(PyGlopsMaterial):

    def __init__(self):
        super(KivyGlopsMaterial, self).__init__()



look_at_none_warning_enable = True

class KivyGlop(PyGlop, Widget):

    #freeAngle = None
    #degreesPerSecond = None
    #freePos = None
    _mesh = None  # the (Kivy) Mesh object
    _calculated_size = None
    _translate_instruction = None
    _rotate_instruction_x = None
    _rotate_instruction_y = None
    _rotate_instruction_z = None
    _scale_instruction = None
    _color_instruction = None

    _pivot_scaled_point = None
    _pushmatrix = None
    _updatenormalmatrix = None
    _popmatrix = None

    def __init__(self):
        super(KivyGlop, self).__init__()
        #self.freeAngle = 0.0
        #self.degreesPerSecond = 0.0
        #self.freePos = (10.0,100.0)

        #TODO:
        #self.canvas = RenderContext()
        #self.canvas = RenderContext(compute_normal_mat=True)
        self.canvas = InstructionGroup()

        self._calculated_size = (1.0,1.0)  #finish this--or skip since only needed for getting pivot point
        #Rotate(angle=self.freeAngle, origin=(self._calculated_size[0]/2.0,self._calculated_size[1]/2.0))
        self._pivot_point = 0.0, 0.0, 0.0  #self.get_center_average_of_vertices()
        self._pivot_scaled_point = 0.0, 0.0, 0.0
        self._rotate_instruction_x = Rotate(0, 1, 0, 0)  #angle, x, y z
        self._rotate_instruction_x.origin = self._pivot_scaled_point
        self._rotate_instruction_y = Rotate(0, 0, 1, 0)  #angle, x, y z
        self._rotate_instruction_y.origin = self._pivot_scaled_point
        self._rotate_instruction_z = Rotate(0, 0, 0, 1)  #angle, x, y z
        self._rotate_instruction_z.origin = self._pivot_scaled_point
        self._scale_instruction = Scale(1.0,1.0,1.0)
        #self._scale_instruction.origin = self._pivot_point
        self._translate_instruction = Translate(0, 0, 0)
        self._color_instruction = Color(Color(1.0, 1.0, 1.0, 1.0))  # TODO: eliminate this in favor of canvas["mat_diffuse_color"]

    def look_at(self, target_glop):
        if target_glop is not None:
            pitch = 0.0
            pitch = getAngleBetweenPoints(self._translate_instruction.y, self._translate_instruction.z, target_glop._translate_instruction.y, target_glop._translate_instruction.z)
            self._rotate_instruction_x.angle = pitch
            yaw = getAngleBetweenPoints(self._translate_instruction.x, self._translate_instruction.z, target_glop._translate_instruction.x, target_glop._translate_instruction.z)
            self._rotate_instruction_y.angle = yaw
            #print("look at pitch,yaw: "+str(int(math.degrees(pitch)))+","+str(int(math.degrees(yaw))))
        else:
            global look_at_none_warning_enable
            if look_at_none_warning_enable:
                print("Tried to look at None")
                look_at_none_warning_enable = False

    def copy_as_mesh_instance(self):
        result = KivyGlop()
        result.name = self.name
        context = result.get_context()
        result._translate_instruction.x = self._translate_instruction.x
        result._translate_instruction.y = self._translate_instruction.y
        result._translate_instruction.z = self._translate_instruction.z
        result._rotate_instruction_x.angle = self._rotate_instruction_x.angle
        result._rotate_instruction_y.angle = self._rotate_instruction_y.angle
        result._rotate_instruction_z.angle = self._rotate_instruction_z.angle
        #result._scale_instruction.x = self._scale_instruction.x
        #result._scale_instruction.y = self._scale_instruction.y
        #result._scale_instruction.z = self._scale_instruction.z
        #result._color_instruction.r = self._color_instruction.r
        #result._color_instruction.g = self._color_instruction.g
        #result._color_instruction.b = self._color_instruction.b
        result._pushmatrix = PushMatrix()
        result._updatenormalmatrix = UpdateNormalMatrix()
        result._popmatrix = PopMatrix()

        context.add(result._pushmatrix)
        context.add(result._translate_instruction)
        context.add(result._rotate_instruction_x)
        context.add(result._rotate_instruction_y)
        context.add(result._rotate_instruction_z)
        context.add(result._scale_instruction)
        context.add(result._updatenormalmatrix)
        #context.add(this_glop._color_instruction)  #TODO: asdf add as uniform instead
        if self._mesh is not None:
            context.add(self._mesh)
        else:
            print("WARNING in copy_as_mesh_instance: meshless glop '"+str(self.name)+"'")
        context.add(result._popmatrix)

        return result

    def calculate_hit_range(self):
        #TODO: re-implement superclass method, changing hit box taking rotation into account
        print("  calculate_hit_range for glop ["+str(self.index)+"]...")
        if self.vertices is not None:
            vertex_count = int(len(self.vertices)/self.vertex_depth)
            if vertex_count>0:
                v_offset = 0
                self.hit_radius = 0.0
                for i in range(0,3):
                    #intentionally set to rediculously far in opposite direction:
                    self.hitbox.minimums[i] = sys.maxsize
                    self.hitbox.maximums[i] = -sys.maxsize
                for v_number in range(0, vertex_count):
                    for i in range(0,3):
                        if self.vertices[v_offset+self._POSITION_OFFSET+i] < self.hitbox.minimums[i]:
                            self.hitbox.minimums[i] = self.vertices[v_offset+self._POSITION_OFFSET+i]
                        if self.vertices[v_offset+self._POSITION_OFFSET+i] > self.hitbox.maximums[i]:
                            self.hitbox.maximums[i] = self.vertices[v_offset+self._POSITION_OFFSET+i]
                    this_vertex_relative_distance = get_distance_vec3(self.vertices[v_offset+self._POSITION_OFFSET:v_offset+self._POSITION_OFFSET+3], self._pivot_point)
                    if this_vertex_relative_distance > self.hit_radius:
                        self.hit_radius = this_vertex_relative_distance
                    v_offset += self.vertex_depth
                print("    done.")
            else:
                self.hitbox = None  # avoid 0-size hitbot which would prevent bumps
                if self.hit_radius is None:
                    self.hit_radius = .5
                print("    skipped (0 vertices).")
        else:
            self.hitbox = None  # avoid 0-size hitbot which would prevent bumps
            if self.hit_radius is None:
                self.hit_radius = .5
            print("    skipped (vertices: None).")
                

    def get_context(self):
        return self.canvas

    def rotate_x_relative(self, angle):
        self._rotate_instruction_x.angle += angle

    def rotate_y_relative(self, angle):
        self._rotate_instruction_y.angle += angle

    def rotate_z_relative(self, angle):
        self._rotate_instruction_z.angle += angle

    def move_x_relative(self, distance):
        self._translate_instruction.x += distance

    def move_y_relative(self, distance):
        self._translate_instruction.y += distance

    def move_z_relative(self, distance):
        self._translate_instruction.z += distance

    def transform_pivot_to_geometry(self):
        super(KivyGlop, self).transform_pivot_to_geometry()
        #self._change_instructions()
        self._on_change_pivot()

    def _on_change_pivot(self):
        super(KivyGlop, self)._on_change_pivot()
        self._on_change_scale_instruction()

    def get_scale(self):
        return (self._scale_instruction.x + self._scale_instruction.y + self._scale_instruction.z) / 3.0

    def set_scale(self, overall_scale):
        self._scale_instruction.x = overall_scale
        self._scale_instruction.y = overall_scale
        self._scale_instruction.z = overall_scale
        self._on_change_scale_instruction()

    def _on_change_scale_instruction(self):
        if self._pivot_point is not None:
            self._pivot_scaled_point = self._pivot_point[0]*self._scale_instruction.x+self._translate_instruction.x, self._pivot_point[1]*self._scale_instruction.y+self._translate_instruction.y, self._pivot_point[2]*self._scale_instruction.z+self._translate_instruction.z
#         else:
#             self._pivot_point = 0,0,0
#             self._pivot_scaled_point = 0,0,0
        #super(KivyGlop, self)._on_change_scale()
        #if self._pivot_point is not None:
        self._rotate_instruction_x.origin = self._pivot_scaled_point
        self._rotate_instruction_y.origin = self._pivot_scaled_point
        self._rotate_instruction_z.origin = self._pivot_scaled_point
        #self._translate_instruction.x = self.freePos[0]-self._rectangle_instruction.size[0]*self._scale_instruction.x/2
        #self._translate_instruction.y = self.freePos[1]-self._rectangle_instruction.size[1]*self._scale_instruction.y/2
        #self._rotate_instruction.origin = self._rectangle_instruction.size[0]*self._scale_instruction.x/2.0, self._rectangle_instruction.size[1]*self._scale_instruction.x/2.0
        #self._rotate_instruction.angle = self.freeAngle
        this_name = ""
        if self.name is not None:
            this_name = self.name
        #print()
        #print("_on_change_scale_instruction for object named '"+this_name+"'")
        #print ("_pivot_point:"+str(self._pivot_point))
        #print ("_pivot_scaled_point:"+str(self._pivot_scaled_point))

    def apply_translate(self):
        vertex_count = int(len(self.vertices)/self.vertex_depth)
        v_offset = 0
        for v_number in range(0, vertex_count):
            self.vertices[v_offset+self._POSITION_OFFSET+0] -= self._translate_instruction.x
            self.vertices[v_offset+self._POSITION_OFFSET+1] -= self._translate_instruction.y
            self.vertices[v_offset+self._POSITION_OFFSET+2] -= self._translate_instruction.z
            self._pivot_point = (self._pivot_point[0] - self._translate_instruction.x,
                                 self._pivot_point[1] - self._translate_instruction.y,
                                 self._pivot_point[2] - self._translate_instruction.z)
            self._translate_instruction.x = 0.0
            self._translate_instruction.y = 0.0
            self._translate_instruction.z = 0.0
            v_offset += self.vertex_depth
        self.apply_pivot()

    def set_texture_diffuse(self, path):
        self.last_loaded_path = path
        this_texture_image = None
        if self.last_loaded_path is not None:
            participle = "getting image filename"
            try:
                participle = "loading "+self.last_loaded_path
                if os.path.isfile(self.last_loaded_path):
                    this_texture_image = Image(self.last_loaded_path)
                else:
                    this_texture_image = Image(resource_find(self.last_loaded_path))
                print("Loaded texture '"+str(self.last_loaded_path)+"'")
            except:
                print("Could not finish loading texture: " + str(self.last_loaded_path))
                view_traceback()
        else:
            if verbose_enable:
                Logger.debug("Warning: no texture specified for glop named '"+this_mesh_name+"'")
                this_material_name = ""
                if self.material is not None:
                    if self.material.name is not None:
                        this_material_name = self.material.name
                        Logger.debug("(material named '"+this_material_name+"')")
                    else:
                        Logger.debug("(material with no name)")
                else:
                    Logger.debug("(no material)")
        if self._mesh is not None and this_texture_image is not None:
            self._mesh.texture = this_texture_image.texture
        return this_texture_image

    def push_glop_item(self, this_glop, this_glop_index):
        #item_dict = {}
        item_dict = this_glop.item_dict
        #item_dict["glop_index"] = this_glop_index  #already done when set as item
        #item_dict["glop_name"] = this_glop.name  #already done when set as item
        return self.push_item(item_dict)


    def pop_glop_item(self, this_glop_index):
        select_item_event_dict = None
        #select_item_event_dict["is_possible"] = False
        try:
            if this_glop_index < len(self.properties["inventory_items"]) and this_glop_index>=0:
                #select_item_event_dict["is_possible"] = True
                #self.properties["inventory_items"].pop(this_glop_index)
                self.properties["inventory_items"][this_glop_index] = EMPTY_ITEM
                if this_glop_index == 0:
                    select_item_event_dict = self.select_next_inventory_slot(True)
                else:
                    select_item_event_dict = self.select_next_inventory_slot(False)
                if select_item_event_dict is not None:
                    if "calling_method" in select_item_event_dict:
                        select_item_event_dict["calling_method"] += " from pop_glop_item"
                    else:
                        select_item_event_dict["calling_method"] = "from pop_glop_item"
        except:
            print("Could not finish pop_glop_item:")
            view_traceback()
        return select_item_event_dict

    def generate_kivy_mesh(self):
        participle = "checking for texture"
        self._mesh = None
        this_texture_image = self.set_texture_diffuse(self.get_texture_diffuse_path())
        participle = "assembling kivy Mesh"
        this_texture = None
        if len(self.vertices)>0:
            if (this_texture_image is not None):
                this_texture = this_texture_image.texture
                this_texture.wrap = 'repeat'  # does same as GL_REPEAT -- see https://gist.github.com/tshirtman/3868962#file-main-py-L15

            self._mesh = Mesh(
                    vertices=self.vertices,
                    indices=self.indices,
                    fmt=self.vertex_format,
                    mode='triangles',
                    texture=this_texture,
                )
            if verbose_enable:
                print(str(len(self.vertices))+" vert(ex/ices)")

        else:
            print("WARNING: 0 vertices in glop")
            if self.name is not None:
                print("  named "+self.name)


class KivyGlops(PyGlops):

    #region moved from ui
    IsVisualDebugMode = False
    projection_near = None
    look_point = None
    focal_distance = None  # exists so look_point has more freedom
    camera_walk_units_per_second = None
    selected_glop = None
    selected_glop_index = None
    mode = None
    # moving_x = 0.0
    # moving_z = 0.0
    # _turning_y = 0.0
    controllers = None
    player1_controller = None
    _previous_world_light_dir = None
    _previous_camera_rotate_y_angle = None
    _world_cube = None
    world_boundary_min = None
    world_boundary_max = None
    _sounds = None
    _visual_debug_enable = None
    #endregion moved from ui    

    def __init__(self):
        super(KivyGlops, self).__init__()
        self.controllers = list()
        #region moved from ui
        self._visual_debug_enable = False
        self.world_boundary_min = [None,None,None]
        self.world_boundary_max = [None,None,None]
        self.camera_walk_units_per_second = 12.0
        self.camera_turn_radians_per_second = math.radians(90.0)
        self.mode = MODE_EDIT
        self.player1_controller = PyRealTimeController()
        self.controllers.append(self.player1_controller)
        self.focal_distance = 2.0
        self.projection_near = 0.1
        self._sounds = {}
        
        #x,y,z where y is up:
        self.camera_glop._translate_instruction.x = 0
        self.camera_glop._translate_instruction.y = self.camera_glop.eye_height
        self.camera_glop._translate_instruction.z = 25


        #This is done axis by axis--the only reason is so that you can do OpenGL 6 (boundary detection) lesson from expertmultimedia.com starting with this file
        if self.world_boundary_min[0] is not None:
            if self.camera_glop._translate_instruction.x < self.world_boundary_min[0]:
                self.camera_glop._translate_instruction.x = self.world_boundary_min[0]
        if self.world_boundary_min[1] is not None:
            if self.camera_glop._translate_instruction.y < self.world_boundary_min[1]: #this is done only for this axis, just so that you can do OpenGL 6 lesson using this file (boundary detection)
                self.camera_glop._translate_instruction.y = self.world_boundary_min[1]
        if self.world_boundary_min[2] is not None:
            if self.camera_glop._translate_instruction.z < self.world_boundary_min[2]: #this is done only for this axis, just so that you can do OpenGL 6 lesson using this file (boundary detection)
                self.camera_glop._translate_instruction.z = self.world_boundary_min[2]
        self.camera_glop._rotate_instruction_x.angle = 0.0
        self.camera_glop._rotate_instruction_y.angle = math.radians(-90.0)  # [math.radians(-90.0), 0.0, 1.0, 0.0]
        self.camera_glop._rotate_instruction_z.angle = 0.0
        self.camera_walk_units_per_frame = self.camera_walk_units_per_second / self.frames_per_second
        self.camera_turn_radians_per_frame = self.camera_turn_radians_per_second / self.frames_per_second
        #region moved from ui
        
        self.player_glop = self.camera_glop  # TODO: separate into two objects and make camera follow player
        self.player_glop.bump_enable = True
        self.glops.append(self.camera_glop)
        self.player_glop.name = "Player 1"
        self.glops.append(self.player_glop)
        self.player_glop_index = len(self.glops)-1
        #self._bumper_indices.append(self.player_glop_index)
        this_actor_dict = dict()
        self.set_as_actor_by_index(self.player_glop_index, this_actor_dict)
        #NOTE: set_as_actor_by_index sets hitbox to None if has no vertices

        self.load_glops()  # also moved from ui

    def new_glop(self):
        #return PyGlops.new_glop(self)
        return KivyGlop()

    def create_material(self):
        return KivyGlopsMaterial()

    def hide_glop(self, this_glop):
        self._meshes.remove(this_glop.get_context())
        this_glop.visible_enable = False

    def show_glop(self, this_glop_index):
        self._meshes.add(self.glops[this_glop_index].get_context())
        this_glop.visible_enable = True

    def load_obj(self, source_path, swapyz_enable=False, centered=False):
        results = None
        if swapyz_enable:
            print("NOT YET IMPLEMENTED: swapyz_enable")
        if source_path is not None:
            original_path = source_path
            source_path = resource_find(source_path)
            if source_path is not None:
                if os.path.isfile(source_path):
                    #super(KivyGlops, self).load_obj(source_path)
                    new_glops = self.scene.get_glop_list_from_obj(source_path)
                    if new_glops is None:
                        print("FAILED TO LOAD '"+str(source_path)+"'")
                    elif len(new_glops)<1:
                        print("NO VALID OBJECTS FOUND in '"+str(source_path)+"'")
                    else:
                        if self.scene.glops is None:
                            self.scene.glops = list()

                        #for index in range(0,len(self.glops)):
                        favorite_pivot_point = None
                        for index in range(0,len(new_glops)):
                            #this_glop = new_glops[index]
                            #this_glop = KivyGlop(pyglop=self.glops[index])
                            #if len(self.glops<=index):
                                #self.glops.append(this_glop)
                            #else:
                                #self.glops[index]=this_glop
                            print("")
                            if (favorite_pivot_point is None):
                                favorite_pivot_point = new_glops[index]._pivot_point

                        print("  applying pivot points...")
                        for index in range(0,len(new_glops)):
                            #apply pivot point (so that glop's _translate_instruction is actually the center)
                            prev_pivot = new_glops[index]._pivot_point[0], new_glops[index]._pivot_point[1], new_glops[index]._pivot_point[2]
                            new_glops[index].apply_pivot()
                            #print("    moving from "+str( (new_glops[index]._translate_instruction.x, new_glops[index]._translate_instruction.y, new_glops[index]._translate_instruction.z) ))
                            new_glops[index]._translate_instruction.x = prev_pivot[0]
                            new_glops[index]._translate_instruction.y = prev_pivot[1]
                            new_glops[index]._translate_instruction.z = prev_pivot[2]
                            new_glops[index].generate_kivy_mesh()
                            self.add_glop(new_glops[index])
                            if results is None:
                                results = list()
                            results.append(len(self.scene.glops)-1)
                        if centered:
                            #TODO: apply pivot point instead (change vertices as if pivot point were 0,0,0) to ensure translate 0 is world 0; instead of:
                            #center it (use only one pivot point, so all objects in obj file remain aligned with each other):
                            for index in range(0,len(new_glops)):
                                print("  centering from "+str(favorite_pivot_point))
                                new_glops[index].move_x_relative(-1.0*favorite_pivot_point[0])
                                new_glops[index].move_y_relative(-1.0*favorite_pivot_point[1])
                                new_glops[index].move_z_relative(-1.0*favorite_pivot_point[2])
                                #TODO: new_glops[index].apply_translate()
                                #TODO: new_glops[index].reset_translate()

                        print("")
                else:
                    print("missing '"+source_path+"'")
            else:
                print("missing '"+original_path+"'")
        else:
            print("ERROR: source_path is None for load_obj")
        return results

        
    def update(self):
        super(KivyGlops, self).update()

        self.hud_form.pos = 0.0, 0.0
        self.hud_form.size = Window.size
        if self.hud_bg_rect is not None:
            self.hud_bg_rect.size = self.hud_form.size
            self.hud_bg_rect.pos=self.hud_form.pos

        #if verbose_enable:
        #    print("update_glsl...")
        asp = float(self.width) / float(self.height)

        clip_top = 0.06  #NOTE: 0.03 is ~1.72 degrees, if that matters
        # formerly field_of_view_factor
        # was changed to .03 when projection_near was changed from 1 to .1
        # was .3 when projection_near was 1

        clip_right = asp*clip_top  # formerly overwrote asp
        proj = Matrix()
        modelViewMatrix = Matrix()

        #modelViewMatrix.rotate(self.scene.camera_glop._rotate_instruction_x.angle,1.0,0.0,0.0)
        #modelViewMatrix.rotate(self.scene.camera_glop._rotate_instruction_y.angle,0.0,1.0,0.0)
        #look_at(eyeX, eyeY, eyeZ, centerX, centerY, centerZ, upX, upY, upZ)  $http://kivy.org/docs/api-kivy.graphics.transformation.html
        #modelViewMatrix.rotate(self.scene.camera_glop._rotate_instruction_z.angle,0.0,0.0,1.0)
        previous_look_point = None
        if self.look_point is not None:
            previous_look_point = self.look_point[0], self.look_point[1], self.look_point[2]

        self.look_point = [0.0,0.0,0.0]

        #0 is the angle (1, 2, and 3 are the matrix)
        self.look_point[0] = self.focal_distance * math.cos(self.scene.camera_glop._rotate_instruction_y.angle)
        self.look_point[2] = self.focal_distance * math.sin(self.scene.camera_glop._rotate_instruction_y.angle)

        #self.look_point[1] = 0.0  #(changed in "for" loop below) since y is up, and 1 is y, ignore index 1 when we are rotating on that axis
        self.look_point[1] = self.focal_distance * math.sin(self.scene.camera_glop._rotate_instruction_x.angle)


        #modelViewMatrix = modelViewMatrix.look_at(0,self.scene.camera_glop._translate_instruction.y,0, self.look_point[0], self.look_point[1], self.look_point[2], 0, 1, 0)

        #Since what you are looking at should be relative to yourself, add camera's position:

        self.look_point[0] += self.scene.camera_glop._translate_instruction.x
        self.look_point[1] += self.scene.camera_glop._translate_instruction.y
        self.look_point[2] += self.scene.camera_glop._translate_instruction.z

        #must translate first, otherwise look_at will override position on rotation axis ('y' in this case)
        modelViewMatrix.translate(self.scene.camera_glop._translate_instruction.x, self.scene.camera_glop._translate_instruction.y, self.scene.camera_glop._translate_instruction.z)
        #moving_theta = theta_radians_from_rectangular(moving_x, moving_z)
        modelViewMatrix = modelViewMatrix.look_at(self.scene.camera_glop._translate_instruction.x, self.scene.camera_glop._translate_instruction.y, self.scene.camera_glop._translate_instruction.z, self.look_point[0], self.look_point[1], self.look_point[2], 0, 1, 0)



        #proj.view_clip(left, right, bottom, top, near, far, perspective)
        #"In OpenGL, a 3D point in eye space is projected onto the near plane (projection plane)"
        # -http://www.songho.ca/opengl/gl_projectionmatrix.html
        #The near plane and far plane distances are in the -z direction but are
        # expressed as positive values since they are distances from the camera
        # then they are compressed to -1 to 1
        # -https://www.youtube.com/watch?v=frtzb2WWECg
        proj = proj.view_clip(-clip_right, clip_right, -1*clip_top, clip_top, self.projection_near, 100, 1)
        top_theta = theta_radians_from_rectangular(self.projection_near, clip_top)
        right_theta = theta_radians_from_rectangular(self.projection_near, clip_right)
        self.screen_w_arc_theta = right_theta*2.0
        self.screen_h_arc_theta = top_theta*2.0

        self.gl_widget.canvas['projection_mat'] = proj
        self.gl_widget.canvas['modelview_mat'] = modelViewMatrix
        self.gl_widget.canvas["camera_world_pos"] = [self.scene.camera_glop._translate_instruction.x, self.scene.camera_glop._translate_instruction.y, self.scene.camera_glop._translate_instruction.z]
        #if verbose_enable:
        #    Logger.debug("ok (update_glsl)")

        #is_look_point_changed = False
        #if previous_look_point is not None:
        #    for axis_index in range(3):
        #        if self.look_point[axis_index] != previous_look_point[axis_index]:
        #            is_look_point_changed = True
        #            #print(str(self.look_point)+" was "+str(previous_look_point))
        #            break
        #else:
        #    is_look_point_changed = True
        #
        #if is_look_point_changed:
        #    #print("Now looking at "+str(self.look_point))
        #    #print ("position: "+str( (self.scene.camera_glop._translate_instruction.x, self.scene.camera_glop._translate_instruction.y, self.scene.camera_glop._translate_instruction.z) )+"; self.scene.camera_glop._rotate_instruction_y.angle:"+str(self.scene.camera_glop._rotate_instruction_y.angle) +"("+str(math.degrees(self.scene.camera_glop._rotate_instruction_y.angle))+"degrees); moving_theta:"+str(math.degrees(moving_theta))+" degrees")

        if (self._previous_world_light_dir is None
            or self._previous_world_light_dir[0]!=self.gl_widget.canvas["_world_light_dir"][0]
            or self._previous_world_light_dir[1]!=self.gl_widget.canvas["_world_light_dir"][1]
            or self._previous_world_light_dir[2]!=self.gl_widget.canvas["_world_light_dir"][2]
            or self._previous_camera_rotate_y_angle is None
            or self._previous_camera_rotate_y_angle != self.scene.camera_glop._rotate_instruction_y.angle
            ):
            #self.gl_widget.canvas["_world_light_dir"] = (0.0,.5,1.0);
            #self.gl_widget.canvas["_world_light_dir_eye_space"] = (0.0,.5,1.0);
            world_light_theta = theta_radians_from_rectangular(self.gl_widget.canvas["_world_light_dir"][0], self.gl_widget.canvas["_world_light_dir"][2])
            light_theta = world_light_theta+self.scene.camera_glop._rotate_instruction_y.angle
            light_r = math.sqrt((self.gl_widget.canvas["_world_light_dir"][0]*self.gl_widget.canvas["_world_light_dir"][0])+(self.gl_widget.canvas["_world_light_dir"][2]*self.gl_widget.canvas["_world_light_dir"][2]))
            self.gl_widget.canvas["_world_light_dir_eye_space"] = light_r * math.cos(light_theta), self.gl_widget.canvas["_world_light_dir_eye_space"][1], light_r * math.sin(light_theta)
            self._previous_camera_rotate_y_angle = self.scene.camera_glop._rotate_instruction_y.angle
            self._previous_world_light_dir = self.gl_widget.canvas["_world_light_dir"][0], self.gl_widget.canvas["_world_light_dir"][1], self.gl_widget.canvas["_world_light_dir"][2]
        


class GLWidget(Widget):
    pass


class HudForm(BoxLayout):
    pass


class ContainerForm(BoxLayout):
    pass


class KivyGlopsWindow(ContainerForm):  # formerly a subclass of Widget
    #region Window
    hud_form = None
    hud_buttons_form = None
    _meshes = None # so gl operations can be added in realtime (after resetCallback is added, but so resetCallback is on the stack after them)
    gl_widget = None
    scene = None  # only use for drawing frames and sending input
    #endregion Window
    #region Window TODO: rename to _*
    use_button = None  
    screen_w_arc_theta = None
    screen_h_arc_theta = None
    hud_bg_rect = None
    env_rectangle = None
    #endregion Window TODO: rename to _*
    


    def __init__(self, **kwargs):
        self.scene = KivyGlops()
        self.scene.ui = self
        self.gl_widget = GLWidget()
        self.hud_form = HudForm(orientation="vertical", size_hint=(1.0, 1.0))
        self.hud_buttons_form = BoxLayout(orientation="horizontal",
                                          size_hint=(1.0, 0.1))

        #fix incorrect keycodes if present (such as in kivy <= 1.8.0):
        if (Keyboard.keycodes["-"]==41):
            Keyboard.keycodes["-"]=45
        if (Keyboard.keycodes["="]==43):
            Keyboard.keycodes["="]=61
        
        try:
            self._keyboard = Window.request_keyboard(
                self._keyboard_closed, self)
            self._keyboard.bind(on_key_down=self._on_keyboard_down)
            self._keyboard.bind(on_key_up=self._on_keyboard_up)
        except:
            print("Could not finish loading keyboard" +
                  "(keyboard may not be present).")

        #self.bind(on_touch_down=self.canvasTouchDown)

        self.gl_widget.canvas = RenderContext(compute_normal_mat=True)
        self.gl_widget.canvas["_world_light_dir"] = (0.0, 0.5, 1.0)
        self.gl_widget.canvas["_world_light_dir_eye_space"] = (0.0, 0.5, 1.0) #rotated in update_glsl
        self.gl_widget.canvas["camera_light_multiplier"] = (1.0, 1.0, 1.0, 1.0)
        #self.gl_widget.canvas.shader.source = resource_find('simple1b.glsl')
        #self.gl_widget.canvas.shader.source = resource_find('shade-kivyglops-standard.glsl')  # NOT working
        #self.gl_widget.canvas.shader.source = resource_find('shade-normal-only.glsl') #partially working
        #self.gl_widget.canvas.shader.source = resource_find('shade-texture-only.glsl')
        #self.gl_widget.canvas.shader.source = resource_find('shade-kivyglops-minimal.glsl')  # NOT working
        self.gl_widget.canvas.shader.source = resource_find('fresnel.glsl')

        #formerly, .obj was loaded here using load_obj (now calling program does that)

        #print(self.gl_widget.canvas.shader)  #just prints type and memory address
        if dump_enable:
            glopsYAMLLines = []
            self.scene.append_dump(glopsYAMLLines)
            try:
                thisFile = open('glops-dump.yml', 'w')
                for i in range(0,len(glopsYAMLLines)):
                    thisFile.write(glopsYAMLLines[i]+"\n")
                thisFile.close()
            except:
                print("Could not finish writing dump.")
        super(KivyGlopsWindow, self).__init__(**kwargs)
        self.cb = Callback(self.setup_gl_context)
        self.gl_widget.canvas.add(self.cb)

        self.gl_widget.canvas.add(PushMatrix())

        #self.gl_widget.canvas.add(PushMatrix())
        #self.gl_widget.canvas.add(this_texture)
        #self.gl_widget.canvas.add(Color(1, 1, 1, 1))
        #for this_glop_index in range(0,len(self.scene.glops)):
        #    this_mesh_name = ""
        #    #thisMesh = KivyGlop()
        #    this_glop = self.scene.glops[this_glop_index]
        #    add_glop(this_glop)
        #self.gl_widget.canvas.add(PopMatrix())
        self._meshes = InstructionGroup() #RenderContext(compute_normal_mat=True)
        self.gl_widget.canvas.add(self._meshes)

        self.ui.finalize_canvas()
        self.add_widget(self.gl_widget)
        #self.hud_form.rows = 1
        self.add_widget(self.hud_form)

        self.debug_label = Factory.Label(text="...")
        if not self.ui._visual_debug_enable:
            self.debug_label.opacity = 0.0
        self.hud_form.add_widget(self.debug_label)
        self.hud_form.add_widget(self.hud_buttons_form)
        self.inventory_prev_button = Factory.Button(text="<", id="inventory_prev_button", size_hint=(.2,1.0), on_press=self.inventory_prev_button_press)
        self.use_button = Factory.Button(text="0: Empty", id="use_button", size_hint=(.2,1.0), on_press=self.inventory_use_button_press)
        self.inventory_next_button = Factory.Button(text=">", id="inventory_next_button", size_hint=(.2,1.0), on_press=self.inventory_next_button_press)
        self.hud_buttons_form.add_widget(self.inventory_prev_button)
        self.hud_buttons_form.add_widget(self.use_button)
        self.hud_buttons_form.add_widget(self.inventory_next_button)

        #Window.bind(on_motion=self.on_motion)  #TODO ?: formerly didn't work, but maybe failed since used Window. instead of self--see <https://kivy.org/docs/api-kivy.input.motionevent.html>
        
        Clock.schedule_interval(self.update_glsl, 1.0 / self.scene.frames_per_second)
        
        self._touches = []

    def set_hud_background(self, path):
        if path is not None:
            original_path = path
            if not os.path.isfile(path):
                path = resource_find(path)
            if path is not None:
                self.hud_form.canvas.before.clear()
                #self.hud_form.canvas.before.add(Color(1.0,1.0,1.0,1.0))
                self.hud_bg_rect = Rectangle(size=self.hud_form.size,
                                             pos=self.hud_form.pos,
                                             source=path)
                self.hud_form.canvas.before.add(self.hud_bg_rect)
                self.hud_form.source = path
            else:
                print("ERROR in set_hud_image: could not find "+original_path)
        else:
            print("ERROR in set_hud_image: path is None")

    def spawn_pex_particles(self, path, pos, radius=1.0, duration_seconds=None):
        if path is not None:
            if os.path.isfile(path):
                print("found '" + path + "'")
                print("  (not yet implemented)")
                #Range is 0 to 250px for size, so therefore translate to meters:
                # divide by 125 to get meters, then multiply by radius,
                # so that pex file can determine "extra" (>125)
                # or "reduced" (<125) size while retaining pixel-based sizing.
            else:
                print("missing '" + path + "'")
        else:
            print("ERROR in spawn_pex_particles: path is None")

    def set_background_cylmap(self, path):
        #self.load_obj("env_sphere.obj")
        #self.load_obj("maps/gi/etc/sky_sphere.obj")
        #env_indices = self.get_indices_by_source_path("env_sphere.obj")
        #for i in range(0,len(env_indices)):
        #    index = env_indices[i]
        #    print("Preparing sky object "+str(index))
        #    self.scene.glops[index].set_texture_diffuse(path)
        if self.env_rectangle is not None:
            self.canvas.before.remove(self.env_rectangle)
        original_path = path
        if path is not None:
            if not os.path.isfile(path):
                path = resource_find(path)
            if path is not None:
                #texture = CoreImage(path).texture
                #texture.wrap = repeat
                #self.env_rectangle = Rectangle(texture=texture)
                self.env_rectangle = Rectangle(source=path)
                self.env_rectangle.texture.wrap = "repeat"
                self.canvas.before.add(self.env_rectangle)
            else:
                print("ERROR in set_background_cylmap: "+original_path+" not found in search path")
        else:
            print("ERROR in set_background_cylmap: path is None")


    def preload_sound(self, path):
        if path is not None:
            if path not in self._sounds:
                self._sounds[path] = {}
                print("loading "+path)
                self._sounds[path]["loader"] = SoundLoader.load(path)

    def play_sound(self, path, loop=False):
        if path is not None:
            self.preload_sound(path)
            if self._sounds[path]:
                if verbose_enable:
                    print("playing "+path)
                self._sounds[path]["loader"].play()
            else:
                print("Failed to play "+path)
        else:
            print("ERROR in play_sound: path is None")

    def play_music(self, path, loop=True):
        self.play_sound(path, loop=loop)  #TODO: handle on_stop and play again if loop=True

    def explode_glop_by_index(self, index, weapon_dict=None):
        self.display_explosion( \
            get_vec3_from_point(self.scene.glops[index]._translate_instruction), \
            self.scene.glops[index].hit_radius, \
            index,
            weapon_dict)
        self.kill_glop_by_index(index, weapon_dict)

    def display_explosion(self, pos, radius, attacked_index, weapon_dict):
        print("subclass should implement display_explosion" + \
            " (allowing variables other than pos to be None)")


    def inventory_prev_button_press(self, instance):
        event_dict = self.scene.camera_glop.select_next_inventory_slot(False)
        self.scene.after_selected_item(event_dict)

    def inventory_use_button_press(self, instance):
        event_dict = self.use_selected(self.scene.camera_glop)
        #self.scene.after_selected_item(event_dict)

    def inventory_next_button_press(self, instance):
        event_dict = self.scene.camera_glop.select_next_inventory_slot(True)
        self.scene.after_selected_item(event_dict)

    def finalize_canvas(self):
        self.gl_widget.canvas.add(PopMatrix())

        self.resetCallback = Callback(self.reset_gl_context)
        self.gl_widget.canvas.add(self.resetCallback)


    #def hide_glop(self, this_glop):
    #    self.scene.hide_glop(this_glop)
    
    #def show_glop(self, this_glop_index):
    #    self.scene.show_glop(this_glop_index)

    def add_glop(self, this_glop):
        participle="initializing"
        try:
            this_glop.visible_enable = True
            #context = self._meshes
            #context = self.gl_widget.canvas
            #if self.selected_glop_index is None:
            #    self.selected_glop_index = this_glop_index
            #    self.selected_glop = this_glop
            self.selected_glop_index = len(self.scene.glops)
            self.selected_glop = this_glop
            context = this_glop.get_context()
            this_mesh_name = ""
            if this_glop.name is not None:
                this_mesh_name = this_glop.name
            #this_glop._scale_instruction = Scale(0.6)
            this_glop._pushmatrix = PushMatrix()
            this_glop._updatenormalmatrix = UpdateNormalMatrix()
            this_glop._popmatrix = PopMatrix()

            context.add(this_glop._pushmatrix)
            context.add(this_glop._translate_instruction)
            context.add(this_glop._rotate_instruction_x)
            context.add(this_glop._rotate_instruction_y)
            context.add(this_glop._rotate_instruction_z)
            context.add(this_glop._scale_instruction)
            context.add(this_glop._updatenormalmatrix)

            #context.add(this_glop._color_instruction)  #TODO: asdf add as uniform instead
            if this_glop._mesh is None:
                this_glop.generate_kivy_mesh()
                print("WARNING: glop had no mesh, so was generated when added to render context. Please ensure it is a KivyGlop and not a PyGlop (however, vertex indices misread could also lead to missing Mesh object).")
            print("_color_instruction.r,.g,.b,.a: "+str( [this_glop._color_instruction.r, this_glop._color_instruction.g, this_glop._color_instruction.b, this_glop._color_instruction.a] ))
            print("u_color: "+str(this_glop.material.diffuse_color))

            if this_glop._mesh is not None:
                context.add(this_glop._mesh)
                if verbose_enable:
                    print("Added mesh to render context.")
            else:
                print("NOT adding mesh.")
            context.add(this_glop._popmatrix)
            if self.scene.glops is None:
                self.scene.glops = list()


            self.scene.glops.append(this_glop)
            self.scene.glops[len(self.scene.glops)-1].index = len(self.scene.glops) - 1
            #this_glop.index = len(self.scene.glops) - 1
            self._meshes.add(self.scene.glops[len(self.scene.glops)-1].get_context())  # _meshes is a visible instruction group
            self.scene.glops[len(self.scene.glops)-1].visible_enable = True

            if verbose_enable:
                print("Appended Glop (count:"+str(len(self.scene.glops))+").")

        except:
            print("ERROR: Could not finish "+participle+" in KivyGlops load_obj")
            view_traceback()

    def setup_gl_context(self, *args):
        glEnable(GL_DEPTH_TEST)

    def reset_gl_context(self, *args):
        glDisable(GL_DEPTH_TEST)

    def update_glsl(self, *largs):
        self.scene.update()

    #def get_view_angles_by_touch_deg(self, touch):
    #    # formerly define_rotate_angle(self, touch):
    #    x_angle = (touch.dx/self.width)*360
    #    y_angle = -1*(touch.dy/self.height)*360
    #    return x_angle, y_angle

    #def get_view_angles_by_pos_deg(self, pos):
    #    x_angle = (pos[0]/self.width)*360
    #    y_angle = -1*(pos[1]/self.height)*360
    #    return x_angle, y_angle
    
    def update_debug_label(self):
        yaml = ""
        indent = ""
        for key in debug_dict.keys():
            yaml = push_yaml_text(yaml, key, debug_dict[key], indent)
            #if debug_dict[key] is None:
            #    self.debug_label.text = key + ": None"
            #elif type(debug_dict[key]) is dict:
        self.debug_label.text = yaml
        

#     def canvasTouchDown(self, touch, *largs):
#         touchX, touchY = largs[0].pos
#         #self.player1.targetX = touchX
#         #self.player1.targetY = touchY
#         print("\n")
#         print(str(largs).replace("\" ","\"\n"))

    def on_touch_down(self, touch):
        super(KivyGlopsWindow, self).on_touch_down(touch)
        #touch.grab(self)
        #self._touches.append(touch)

#         thisTouch = MouseMotionEvent(touch)
#         thisTouch.
        if touch.is_mouse_scrolling:
            event_dict = None
            if touch.button == "scrolldown":
                event_dict = self.scene.camera_glop.select_next_inventory_slot(True)
            else:
                event_dict = self.scene.camera_glop.select_next_inventory_slot(False)
            self.after_selected_item(event_dict)
        else:
            event_dict = self.use_selected(self.scene.camera_glop)

    def on_touch_up(self, touch):
        super(KivyGlopsWindow, self).on_touch_up(touch)
        #touch.ungrab(self)
        #self._touches.remove(touch)
        #self.player1_controller.dump()

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
#         print('The key' + str(keycode) + ' pressed')
#         print(' - text is ' + text)
#         print(' - modifiers are '+ str(modifiers))

        #print("pressed keycode "+str(keycode[0])+" (should match keycode constant: "+str(Keyboard.keycodes[keycode[1]])+")")

        #if len(keycode[1])>0:
        self.player1_controller.set_pressed(keycode[0], keycode[1], True)

        # Keycode is composed of an integer + a string
        # If we hit escape, release the keyboard
        if keycode[1] == 'escape':
            pass  #keyboard.release()
        # elif keycode[1] == 'w':
        #     self.scene.camera_glop._translate_instruction.z += self.camera_walk_units_per_frame
        # elif keycode[1] == 's':
        #     self.scene.camera_glop._translate_instruction.z -= self.camera_walk_units_per_frame
        # elif text == 'a':
        #     self.player1_controller["left"] = True
        #     self.moving_x = -1.0
        # elif text == 'd':
        #     self.moving_x = 1.0
        #     self.player1_controller["right"] = True
#         elif keycode[1] == '.':
#             self.look_at_center()
#         elif keycode[1] == 'numpadadd':
#             pass
#         elif keycode[1] == 'numpadsubtract' or keycode[1] == 'numpadsubstract':  #since is mispelled as numpadsubstract in kivy
#             pass
        elif keycode[1] == "tab":
            self.select_mesh_by_index(self.selected_glop_index+1)
            #if verbose_enable:
            this_name = None
            if self.selected_glop_index is not None:
                this_name = "["+str(self.selected_glop_index)+"]"
            if self.selected_glop is not None and self.selected_glop.name is not None:
                this_name = self.selected_glop.name
            if this_name is not None:
                print('Selected glop: '+this_name)
            else:
                print('Select glop failed (maybe there are no glops loaded.')
        elif keycode[1] == "x":
            event_dict = self.scene.camera_glop.select_next_inventory_slot(True)
            self.after_selected_item(event_dict)
        elif keycode[1] == "z":
            event_dict = self.scene.camera_glop.select_next_inventory_slot(False)
            self.after_selected_item(event_dict)
        elif keycode[1] == "f3":
            self.toggle_visual_debug()
        # else:
        #     print('Pressed unused key: ' + str(keycode) + "; text:"+text)

        if verbose_enable:
            self.print_location()
            print("scene.camera_glop._rotate_instruction_y.angle:"+str(self.scene.camera_glop._rotate_instruction_y.angle))
            print("modelview_mat:"+str(self.gl_widget.canvas['modelview_mat']))
        self.update_glsl()
        # Return True to accept the key. Otherwise, it will be used by
        # the system.
        return True

    def _on_keyboard_up(self, keyboard, keycode):
        self.player1_controller.set_pressed(keycode[0], keycode[1], False)
        #print('Released key ' + str(keycode))

    def _keyboard_closed(self):
        print('Keyboard disconnected!')
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    #def on_motion(self, etype, motionevent):
        #print("coords:"+str(motionevent.dx)+","+str(motionevent.dx))
        # will receive all motion events.
        #pass

    def on_touch_move(self, touch):
        #print("touch.dx:"+str(touch.dx)+" touch.dy:"+str(touch.dx))
        pass
#         print ("on_touch_move")
#         print (str(touch))
#         #Logger.debug("dx: %s, dy: %s. Widget: (%s, %s)" % (touch.dx, touch.dy, self.width, self.height))
#         #self.update_glsl()
#         if touch in self._touches and touch.grab_current == self:
#             if len(self._touches) == 1:
#                 # here do just rotation
#                 ax, ay = self.define_rotate_angle(touch)
#
#
#                 self.rotx.angle += ax
#                 self.roty.angle += ay
#
#                 #ax, ay = math.radians(ax), math.radians(ay)
#
#
#             elif len(self._touches) == 2: # scaling here
#                 #use two touches to determine do we need scal
#                 touch1, touch2 = self._touches
#                 old_pos1 = (touch1.x - touch1.dx, touch1.y - touch1.dy)
#                 old_pos2 = (touch2.x - touch2.dx, touch2.y - touch2.dy)
#
#                 old_dx = old_pos1[0] - old_pos2[0]
#                 old_dy = old_pos1[1] - old_pos2[1]
#
#                 old_distance = (old_dx*old_dx + old_dy*old_dy)
#                 Logger.debug('Old distance: %s' % old_distance)
#
#                 new_dx = touch1.x - touch2.x
#                 new_dy = touch1.y - touch2.y
#
#                 new_distance = (new_dx*new_dx + new_dy*new_dy)
#
#                 Logger.debug('New distance: %s' % new_distance)
#                 self.camera_walk_units_per_frame = self.camera_walk_units_per_second / self.scene.frames_per_second
#                 #self.camera_walk_units_per_frame = 0.01
#
#                 if new_distance > old_distance:
#                     scale = -1*self.camera_walk_units_per_frame
#                     Logger.debug('Scale up')
#                 elif new_distance == old_distance:
#                     scale = 0
#                 else:
#                     scale = self.camera_walk_units_per_frame
#                     Logger.debug('Scale down')
#
#                 if scale:
#                     self.scene.camera_glop._translate_instruction.z += scale
#                     print(str(scale) + " " + (self.scene.camera_glop._translate_instruction.x, self.scene.camera_glop._translate_instruction.y, self.scene.camera_glop._translate_instruction.z) )
#             self.update_glsl()

