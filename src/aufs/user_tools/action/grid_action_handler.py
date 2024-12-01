import json
import subprocess
from PySide6.QtWidgets import QMessageBox, QDialog
from .deadline_commands import complete_tasks, fail_tasks, requeue_tasks, suspend_tasks, resume_tasks, generate_submission_info_files
from .region_render_existing_job import RegionRenderExistingJob
from .set_tiles_for_region_render import TileMatrixDialog
from .ec2_wrangler import EC2Wrangler, EC2TerminationProcess, EC2StartProcess, EC2StopProcess, EC2TerminationProtectionProcess

DEADLINE_COMMAND = "/opt/Thinkbox/Deadline10/bin/deadlinecommand"

class gridActionHandler:
    def __init__(self):
        self.handlers = {
            'completeTasks': self.handle_complete_tasks,
            'failTasks': self.handle_fail_tasks,
            'requeueTasks': self.handle_requeue_tasks,
            'suspendTasks': self.handle_suspend_tasks,
            'resumeTasks': self.handle_resume_tasks,
            'regionRenderExistingJob': self.handle_region_render_existing_job,
            'terminateEC2Instances': self.handle_terminate_ec2_instances,
            'startEC2Instances': self.handle_start_ec2_instances,
            'stopEC2Instances': self.handle_stop_ec2_instances,
            'terminationProtectionOFFInstances': self.handle_termination_protection_OFF_instances,
            'terminationProtectionONInstances': self.handle_termination_protection_ON_instances,
        }

    def dictlist_to_tupleslist(self, dict_list, keys):
        """
        Converts a list of dictionaries into a list of tuples based on the specified keys.
        """
        return [(tuple(d[key] for key in keys)) for d in dict_list]

    def process_action(self, action, payload):
        handler = self.handlers.get(action)
        if not handler:
            raise ValueError(f"No handler for action '{action}'")
        return handler(payload)

    def handle_terminate_ec2_instances(self, payload):
        print('Payload from Instance Grid:')
        print(payload)

        instance_details = self.dictlist_to_tupleslist(payload, ['InstanceId', 'Region'])
        regions = list(set(item['Region'] for item in payload))

        wrangler = EC2Wrangler(regions, data_manager=None)
        termination_process = EC2TerminationProcess(instance_details=instance_details,
                                                    ec2_manager=wrangler.ec2_manager,
                                                    object_list_formatter=wrangler.object_list_formatter)
        result = termination_process.execute()
        return json.dumps(result)

    def handle_start_ec2_instances(self, payload):
        print('Payload from Instance Grid (Start):')
        print(payload)

        instance_details = self.dictlist_to_tupleslist(payload, ['InstanceId', 'Region'])
        regions = list(set(item['Region'] for item in payload))

        wrangler = EC2Wrangler(regions, data_manager=None)
        start_process = EC2StartProcess(instance_details=instance_details,
                                        ec2_manager=wrangler.ec2_manager,
                                        object_list_formatter=wrangler.object_list_formatter)
        result = start_process.execute()
        return json.dumps(result)

    def handle_stop_ec2_instances(self, payload):
        print('Payload from Instance Grid (Stop):')
        print(payload)

        instance_details = self.dictlist_to_tupleslist(payload, ['InstanceId', 'Region'])
        regions = list(set(item['Region'] for item in payload))

        wrangler = EC2Wrangler(regions, data_manager=None)
        stop_process = EC2StopProcess(instance_details=instance_details,
                                      ec2_manager=wrangler.ec2_manager,
                                      object_list_formatter=wrangler.object_list_formatter)
        result = stop_process.execute()
        return json.dumps(result)

    def handle_region_render_existing_job(self, payload):
        """
        Handles the submission of a tiled job using the provided payload.
        """
        results = {}

        for item in payload:
            job_id = item['jobid']
            x_tiles = item.get('x_tiles', 3)
            y_tiles = item.get('y_tiles', 4)
            bypass_dialog = item.get('bypass_dialog', False)  # Check for dialog bypass flag

            # Check for 1x1 tile configuration
            if x_tiles == 1 and y_tiles == 1:
                message = ("You're about to submit a job with a 1x1 tile configuration, "
                        "which will create tasks identical to those in the original job. "
                        "This may not save any time or resources. Consider using "
                        "Deadline's 'Resubmit Job' feature instead. Would you like to proceed?")
                reply = QMessageBox.warning(None, '1x1 Tiling Warning', message,
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    results[job_id] = 'Job submission cancelled due to 1x1 tiling configuration'
                    continue

            # Bypass dialog if requested
            if bypass_dialog:
                message = ("Tiling parameters (x_tiles and y_tiles) were provided. "
                        "Would you like to open the dialog to adjust these settings, or exit?")
                reply = QMessageBox.question(None, 'Bypass Dialog', message,
                                            QMessageBox.Open | QMessageBox.Cancel, QMessageBox.Cancel)
                if reply == QMessageBox.Cancel:
                    results[job_id] = 'Job submission cancelled by user'
                    continue

            # Generate submission info files
            job_info_file, plugin_info_file = generate_submission_info_files(job_id)
            if not job_info_file or not plugin_info_file:
                results[job_id] = 'Failed to generate submission info files'
                continue

            # Open the TileMatrixDialog to get the tile configuration
            dialog = TileMatrixDialog(x_tiles=x_tiles, y_tiles=y_tiles)
            if dialog.exec() == QDialog.Accepted:  # Use QDialog.Accepted here
                result = dialog.get_result()
                if len(result) == 2:
                    x_tiles, y_tiles = result
                    tile_numbers = None  # All tiles selected
                else:
                    x_tiles, y_tiles, tile_numbers = result

                # Instantiate the RegionRenderExistingJob with the selected tiles
                region_job = RegionRenderExistingJob(job_id, x_tiles, y_tiles, tile_numbers)
                
                # Modify the generated job_info and plugin_info files before submission
                region_job.submit(job_info_file=job_info_file, plugin_info_file=plugin_info_file)

                results[job_id] = 'Tiled job submitted successfully'
            else:
                results[job_id] = 'Tiled job submission cancelled'

        return json.dumps({'status': 'success', 'results': results})

    def handle_complete_tasks(self, payload):
        return self._handle_tasks(payload, complete_tasks)

    def handle_fail_tasks(self, payload):
        return self._handle_tasks(payload, fail_tasks)

    def handle_requeue_tasks(self, payload):
        return self._handle_tasks(payload, requeue_tasks)

    def handle_suspend_tasks(self, payload):
        return self._handle_tasks(payload, suspend_tasks)

    def handle_resume_tasks(self, payload):
        return self._handle_tasks(payload, resume_tasks)

    def _handle_tasks(self, payload, task_function):
        task_map = self._map_frames_to_task_ids(payload)
        results = {}
        for job_id, task_ids in task_map.items():
            result = task_function(job_id, task_ids)
            results[job_id] = result
        return json.dumps({'status': 'success', 'results': results})

    def _map_frames_to_task_ids(self, payload):
        task_map = {}
        for item in payload:
            job_id = item['jobid']
            frame = str(item['frame'])
            task_id = self._get_task_id(job_id, frame)
            if task_id:
                if job_id not in task_map:
                    task_map[job_id] = []
                task_map[job_id].append(task_id)
        return task_map

    def _get_task_id(self, job_id, frame):
        tasks = self._get_job_tasks(job_id)
        if tasks is None:
            return None
        for task in tasks:
            if task.get('TaskFrameList') == frame:
                return task.get('TaskId')
        return None

    def _get_job_tasks(self, job_id):
        command = [DEADLINE_COMMAND, "GetJobTasks", job_id]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error getting job tasks: {result.stderr}")
            return None
        return self._parse_job_tasks_output(result.stdout)

    def _parse_job_tasks_output(self, output):
        tasks = []
        task = {}
        for line in output.splitlines():
            if line.strip() == "":
                if task:
                    tasks.append(task)
                    task = {}
            else:
                key, value = line.split('=', 1)
                task[key.strip()] = value.strip()
        if task:
            tasks.append(task)
        return tasks

    def handle_termination_protection_ON_instances(self, payload):
        """
        Handles enabling termination protection for the specified EC2 instances.
        """
        return self._handle_termination_protection(payload, enable=True)

    def handle_termination_protection_OFF_instances(self, payload):
        """
        Handles disabling termination protection for the specified EC2 instances.
        """
        return self._handle_termination_protection(payload, enable=False)

    def _handle_termination_protection(self, payload, enable):
        print(f'Payload from Instance Grid (Termination Protection {"ON" if enable else "OFF"}):')
        print(payload)

        instance_details = self.dictlist_to_tupleslist(payload, ['InstanceId', 'Region'])
        regions = list(set(item['Region'] for item in payload))

        wrangler = EC2Wrangler(regions, data_manager=None)
        protection_process = EC2TerminationProtectionProcess(
            instance_details=instance_details,
            ec2_manager=wrangler.ec2_manager,
            object_list_formatter=wrangler.object_list_formatter,
            enable=enable
        )
        result = protection_process.execute()
        return json.dumps(result)