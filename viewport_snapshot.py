bl_info = {
    "name": "Layout快拍",
    "author": "Hermes",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Layout快拍",
    "description": "Quick viewport snapshot to PNG or MP4",
    "category": "3D View",
}

import bpy
import os
from bpy.props import StringProperty, BoolProperty


class SNAPSHOT_OT_get_camera_name(bpy.types.Operator):
    """Fill filename with active scene camera name"""
    bl_idname = "snapshot.get_camera_name"
    bl_label = "Get Camera Name"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        if scene.camera:
            scene.snapshot_filename = scene.camera.name
            self.report({'INFO'}, f"Camera: {scene.camera.name}")
        else:
            self.report({'WARNING'}, "No scene camera")
        return {'FINISHED'}


class SNAPSHOT_OT_get_blend_path(bpy.types.Operator):
    """Fill path with current blend file directory"""
    bl_idname = "snapshot.get_blend_path"
    bl_label = "Get Blend Path"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        blend_path = bpy.data.filepath
        if blend_path:
            scene.snapshot_path = os.path.dirname(blend_path)
            self.report({'INFO'}, f"Path: {scene.snapshot_path}")
        else:
            self.report({'WARNING'}, "Blend file not saved")
        return {'FINISHED'}


class SNAPSHOT_OT_browse_path(bpy.types.Operator):
    """Open file browser to select save directory"""
    bl_idname = "snapshot.browse_path"
    bl_label = "Browse Path"
    bl_options = {'REGISTER'}

    filepath: StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        scene = context.scene
        # filepath from file browser is the selected directory
        scene.snapshot_path = self.filepath
        self.report({'INFO'}, f"Path: {scene.snapshot_path}")
        return {'FINISHED'}

    def invoke(self, context, event):
        # Open file browser in directory selection mode
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SNAPSHOT_OT_safe_frame_one(bpy.types.Operator):
    """Set scene safe frame title to 1.0"""
    bl_idname = "snapshot.safe_frame_one"
    bl_label = "Safe Frame 1.0"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.safe_areas.title = (1.0, 1.0)
        if scene.camera:
            scene.camera.data.show_safe_areas = True
        self.report({'INFO'}, "Safe frame title set to 1.0")
        return {'FINISHED'}


class SNAPSHOT_OT_random_materials(bpy.types.Operator):
    """Create unique material with random base color for each selected object"""
    bl_idname = "snapshot.random_materials"
    bl_label = "Random Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import random
        selected = context.selected_objects
        if not selected:
            self.report({'WARNING'}, "No objects selected")
            return {'CANCELLED'}

        created = 0
        for obj in selected:
            if obj.type != 'MESH':
                continue
            # Create new material
            mat_name = f"MAT_{obj.name}"
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            # Random base color (0.2-1.0 to avoid too dark)
            r = random.uniform(0.2, 1.0)
            g = random.uniform(0.2, 1.0)
            b = random.uniform(0.2, 1.0)
            # Set principled BSDF base color - find by type, not name (works in any language)
            bsdf = None
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    bsdf = node
                    break
            if bsdf:
                bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
            # Assign to object - clear all slots first, then add
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            created += 1

        self.report({'INFO'}, f"Created {created} materials")
        return {'FINISHED'}


class SNAPSHOT_OT_save_image(bpy.types.Operator):
    """Save viewport render as PNG"""
    bl_idname = "snapshot.save_image"
    bl_label = "Save Image (PNG)"
    bl_options = {'REGISTER'}

    filepath: StringProperty(subtype='FILE_PATH')

    def invoke(self, context, event):
        scene = context.scene
        filepath = self._get_filepath(scene, ".png")
        if not filepath:
            return {'CANCELLED'}

        if os.path.exists(filepath):
            # Show confirmation dialog
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        filepath = self._get_filepath(scene, ".png")
        if not filepath:
            return {'CANCELLED'}

        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Set output settings
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = filepath

        # Viewport OpenGL render
        bpy.ops.render.opengl(write_still=True)

        self.report({'INFO'}, f"Saved: {filepath}")
        self._maybe_open_folder(scene, filepath)
        return {'FINISHED'}

    def _get_filepath(self, scene, ext):
        path = scene.snapshot_path.strip()
        filename = scene.snapshot_filename.strip()
        if not path or not filename:
            self.report({'ERROR'}, "Path and filename required")
            return None
        return os.path.join(path, filename + ext)

    def _maybe_open_folder(self, scene, filepath):
        if scene.snapshot_open_folder:
            import subprocess
            import sys
            folder = os.path.dirname(filepath)
            if sys.platform == 'win32':
                os.startfile(folder)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', folder])
            else:
                subprocess.Popen(['xdg-open', folder])


class SNAPSHOT_OT_save_video(bpy.types.Operator):
    """Save viewport animation as MP4"""
    bl_idname = "snapshot.save_video"
    bl_label = "Save Video (MP4)"
    bl_options = {'REGISTER'}

    def invoke(self, context, event):
        scene = context.scene
        filepath = self._get_filepath(scene, ".mp4")
        if not filepath:
            return {'CANCELLED'}

        if os.path.exists(filepath):
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        filepath = self._get_filepath(scene, ".mp4")
        if not filepath:
            return {'CANCELLED'}

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Set output settings for MP4 H.264
        scene.render.image_settings.file_format = 'FFMPEG'
        scene.render.ffmpeg.format = 'MPEG4'
        scene.render.ffmpeg.codec = 'H264'
        scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
        scene.render.filepath = filepath

        # Viewport OpenGL animation render
        bpy.ops.render.opengl(animation=True)

        self.report({'INFO'}, f"Saved: {filepath}")
        self._maybe_open_folder(scene, filepath)
        return {'FINISHED'}

    def _get_filepath(self, scene, ext):
        path = scene.snapshot_path.strip()
        filename = scene.snapshot_filename.strip()
        if not path or not filename:
            self.report({'ERROR'}, "Path and filename required")
            return None
        return os.path.join(path, filename + ext)

    def _maybe_open_folder(self, scene, filepath):
        if scene.snapshot_open_folder:
            import subprocess
            import sys
            folder = os.path.dirname(filepath)
            if sys.platform == 'win32':
                os.startfile(folder)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', folder])
            else:
                subprocess.Popen(['xdg-open', folder])


class SNAPSHOT_PT_panel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_snapshot"
    bl_label = "Layout快拍"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Layout快拍"

    def draw(self, context):
        try:
            layout = self.layout
            scene = context.scene

            # Path + blend path + file browser buttons
            row = layout.row(align=True)
            row.prop(scene, "snapshot_path", text="Path")
            row.operator("snapshot.get_blend_path", text="", icon='ORIENTATION_CURSOR')
            row.operator("snapshot.browse_path", text="", icon='FILEBROWSER')

            # Filename + camera button
            row = layout.row(align=True)
            row.prop(scene, "snapshot_filename", text="Name")
            row.operator("snapshot.get_camera_name", text="", icon='CAMERA_DATA')

            # Open folder checkbox
            layout.prop(scene, "snapshot_open_folder", text="Open folder after save")

            # Buttons
            layout.separator()
            layout.operator("snapshot.save_image", icon='IMAGE_DATA')
            layout.operator("snapshot.save_video", icon='FILE_MOVIE')

            # Camera tools
            layout.separator()
            layout.operator("snapshot.safe_frame_one", icon='CAMERA_DATA')

            # Random materials
            layout.separator()
            layout.operator("snapshot.random_materials", icon='MATERIAL')

            # Camera warning
            if not scene.camera:
                layout.label(text="No scene camera!", icon='ERROR')
        except Exception as e:
            layout = self.layout
            layout.label(text=f"ERROR: {str(e)}")


classes = (
    SNAPSHOT_OT_get_camera_name,
    SNAPSHOT_OT_get_blend_path,
    SNAPSHOT_OT_browse_path,
    SNAPSHOT_OT_safe_frame_one,
    SNAPSHOT_OT_random_materials,
    SNAPSHOT_OT_save_image,
    SNAPSHOT_OT_save_video,
    SNAPSHOT_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.snapshot_path = StringProperty(
        name="Save Path",
        description="Directory to save snapshots",
        default=""
    )
    bpy.types.Scene.snapshot_filename = StringProperty(
        name="Filename",
        description="Base filename (no extension)",
        default="snapshot"
    )
    bpy.types.Scene.snapshot_open_folder = BoolProperty(
        name="Open Folder",
        description="Open containing folder after saving",
        default=False
    )


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.snapshot_path
    del bpy.types.Scene.snapshot_filename
    del bpy.types.Scene.snapshot_open_folder


if __name__ == "__main__":
    register()
