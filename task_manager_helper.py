"""
Task Manager Helper Module

This module provides helper functions for the task manager application.

Classes:
    TaskManagerHelper: Helper class for task management operations
"""

import streamlit as st
import time
import os
from task_manager_interface import TaskManagerInterface
from notion_manager import NotionTaskManager
from sql_manager import SqlTaskManager
from constants import DB_SQLITE, DB_NOTION, DB_OPTIONS
from style_helper import StyleHelper


class TaskManagerHelper:
    """Helper class for task management operations"""
    
    @staticmethod
    def sleep(database_backend: str):
        """
        Sleep for SQLite operations to show visual feedback.
        
        Args:
            database_backend (str): Current database backend (DB_SQLITE or DB_NOTION)
        """
        if database_backend == DB_SQLITE:
            time.sleep(1.5)
    
    @staticmethod
    def show_sidebar_settings() -> str:
        """
        Display sidebar settings and return the selected database backend.
        
        Returns:
            str: Selected database backend (DB_SQLITE or DB_NOTION)
        """
        st.header("⚙️ Settings")
        
        # Radio button with default value SQLite
        backend_options = DB_OPTIONS
        database_backend = st.radio(
            "Choose Database Backend:",
            backend_options,
            index=0,  # Default to SQLite (first option)
            key="database_backend_radio",
            help="Select which database to use for storing tasks"
        )
        
        st.markdown("---")
        
        if database_backend == DB_NOTION:
            st.info("🔗 Using Notion API")
            st.caption("Requires configuration in .streamlit/secrets.toml")
        else:
            st.info("💾 Using Local SQLite")
            st.caption("Data stored in tasks.db file")
        
        st.markdown("---")
        
        # Sync button: Copy from Notion to SQLite
        TaskManagerHelper.show_sync_confirmation_dialog()
        
        return database_backend
    
    @staticmethod
    @st.cache_resource
    def get_task_manager(backend: str) -> TaskManagerInterface:
        """
        Get the appropriate task manager based on the selected backend.
        
        Args:
            backend (str): Either DB_NOTION or DB_SQLITE
        
        Returns:
            TaskManagerInterface: An instance implementing the TaskManagerInterface
        """
        if backend == DB_NOTION:
            try:
                return NotionTaskManager.get_instance()
            except Exception as e:
                st.error(f"❌ Notion configuration error: {e}")
                st.info("💡 Falling back to SQLite. Please configure Notion secrets to use Notion backend.")
                return SqlTaskManager.get_instance()
        else:
            return SqlTaskManager.get_instance()
    
    @staticmethod
    def show_app_header(database_backend: str):
        """
        Display the main app header with backend icon.
        
        Args:
            database_backend (str): Current database backend (DB_SQLITE or DB_NOTION)
        """
        backend_icon = "🔗" if database_backend == DB_NOTION else "💾"
        st.title(f"📋 Task Manager {backend_icon} {database_backend}")
        st.markdown("---")
    
    @staticmethod
    def show_add_task_form(task_manager: TaskManagerInterface):
        """
        Display the add task form and handle task creation.
        
        Args:
            task_manager (TaskManagerInterface): Task manager instance
        """
        st.subheader("➕ Add New Task")
        
        # Form for adding a task
        with st.form("add_task_form", clear_on_submit=True):
            task_name = st.text_input("Task Name:", placeholder="Enter task name...")
            task_status = st.selectbox("Status:", ["Not started", "In progress", "Done"])
            
            submitted = st.form_submit_button("Add Task", type="primary")
            
            if submitted:
                # Validate task name
                if not task_name.strip():
                    st.error("❌ Please provide a task name.")
                else:
                    with st.spinner("Adding task..."):
                        result = task_manager.add_task(task_name, task_status)
                        if result:
                            st.success(f"✅ Task '{task_name}' added successfully!")
                            st.toast("🎉 Task added successfully!", icon="✅")
                        else:
                            st.error("❌ Failed to add task.")
                            st.toast("❌ Failed to add task", icon="⚠️")
    
    @staticmethod
    def show_status_filter() -> str:
        """
        Display the status filter selector.
        
        Returns:
            str: Selected status filter
        """
        st.subheader("🔍 Filter Tasks")
        
        # Initialize session state for programmatic resets only
        if 'status_filter_reset' not in st.session_state:
            st.session_state.status_filter_reset = "All"
        
        # Get the index for reset value (used after clearing tasks by status)
        filter_options = ["All", "Not started", "In progress", "Done"]
        try:
            reset_index = filter_options.index(st.session_state.status_filter_reset)
        except ValueError:
            reset_index = 0
        
        # Use selectbox with key to let Streamlit manage the state naturally
        status_filter = st.selectbox(
            "Filter by status:",
            filter_options,
            index=reset_index,
            key="status_filter_selector"
        )
        
        # Reset the reset value after it's been used
        if st.session_state.status_filter_reset != "All":
            st.session_state.status_filter_reset = "All"
        
        return status_filter
    
    @staticmethod
    def fetch_tasks(task_manager: TaskManagerInterface, status_filter: str) -> list:
        """
        Fetch tasks from the task manager based on status filter.
        
        Args:
            task_manager (TaskManagerInterface): Task manager instance
            status_filter (str): Status filter ("All" or specific status)
        
        Returns:
            list: List of tasks (or None if error occurred)
        """
        with st.spinner("Loading tasks..."):
            if status_filter == "All":
                tasks = task_manager.list_tasks()
            else:
                tasks = task_manager.list_tasks(status_filter)
            
            # Write results to console using os.write
            os.write(1, f"\n📋 Fetched Tasks (Filter: {status_filter}):\n".encode())
            os.write(1, f"Total: {len(tasks) if tasks else 0} tasks\n".encode())
            if tasks:
                for task in tasks:
                    os.write(1, f"  - {task['name']} | Status: {task['status']}\n".encode())
            os.write(1, b"\n")
            
            return tasks
    
    @staticmethod
    def show_task_list(tasks: list, task_manager: TaskManagerInterface, style_helper: StyleHelper, database_backend: str):
        """
        Display the task list with all management features.
        
        Args:
            tasks (list): List of tasks to display
            task_manager (TaskManagerInterface): Task manager instance
            style_helper (StyleHelper): StyleHelper instance for status icons
            database_backend (str): Current database backend (DB_SQLITE or DB_NOTION)
        """
        # Display the table with delete buttons
        st.markdown("<h3 style='text-align: center;'>📊 All Tasks</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        for task in tasks:
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
            with col1:
                # Show task name as text
                st.write(f"**{task['name']}**")
            with col2:
                # Edit button
                if st.button("Edit", key=f"edit_{task['id']}", help="Edit task name", type="secondary"):
                    st.session_state[f"editing_{task['id']}"] = True
                    st.rerun()
            with col3:
                # Create clickable status buttons
                status_options = ["Not started", "In progress", "Done"]
                current_status = task['status']
                
                # Find current status index
                try:
                    current_index = status_options.index(current_status)
                except ValueError:
                    current_index = 0
                
                # Create selectbox for status change
                new_status = st.selectbox(
                    "Status:",
                    status_options,
                    index=current_index,
                    key=f"status_{task['id']}",
                    label_visibility="collapsed"
                )
                
                # Check if status changed
                if new_status != current_status:
                    with st.spinner("Updating status..."):
                        # Add delay for SQLite
                        TaskManagerHelper.sleep(database_backend)
                        # Update task status
                        try:
                            task_manager.update_task_status(task['id'], new_status)
                            st.success(f"✅ Status updated to {new_status}")
                            st.toast(f"🎉 Status changed to {new_status}!", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to update status: {e}")
                            st.toast("❌ Failed to update status", icon="⚠️")
            with col4:
                # Status icon using StyleHelper
                style_helper.create_status_icon(task['status'])
            with col5:
                if st.button("Delete", type="primary", key=f"delete_{task['id']}", help="Delete task"):
                    with st.spinner("Deleting task..."):
                        # Add delay for SQLite
                        TaskManagerHelper.sleep(database_backend)
                        result = task_manager.delete_task(task['id'])
                        if result:
                            st.success(f"✅ Task '{task['name']}' deleted successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete task. Please try again.")
            st.markdown("---")
            
            # Handle editing mode for this specific task - show right below the row
            if st.session_state.get(f"editing_{task['id']}", False):
                col1, col2 = st.columns([3, 2])
                with col1:
                    new_name = st.text_input(
                        "Task Name:",
                        value=task['name'],
                        key=f"edit_name_{task['id']}",
                        label_visibility="visible"
                    )
                with col2:
                    # Buttons container with much closer spacing
                    st.markdown('<div style="padding-top: 1.75rem;">', unsafe_allow_html=True)
                    button_col1, button_col2 = st.columns(2)
                    with button_col1:
                        if st.button("Save", key=f"save_{task['id']}", type="primary", use_container_width=True):
                            if new_name.strip() and new_name != task['name']:
                                with st.spinner("Updating name..."):
                                    # Add delay for SQLite
                                    TaskManagerHelper.sleep(database_backend)
                                    try:
                                        task_manager.update_task_name(task['id'], new_name.strip())
                                        st.success(f"✅ Name updated to '{new_name.strip()}'")
                                        st.toast(f"🎉 Task name updated!", icon="✅")
                                        st.session_state[f"editing_{task['id']}"] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Failed to update name: {e}")
                                        st.toast("❌ Failed to update name", icon="⚠️")
                            else:
                                st.warning("Please enter a different name")
                    with button_col2:
                        if st.button("Cancel", key=f"cancel_{task['id']}", use_container_width=True):
                            st.session_state[f"editing_{task['id']}"] = False
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("---")
    
    @staticmethod
    def show_task_summary(tasks: list, status_filter: str, style_helper: StyleHelper):
        """
        Display task summary metrics.
        
        Args:
            tasks (list): List of tasks
            status_filter (str): Current status filter
            style_helper (StyleHelper): StyleHelper instance for metrics display
        """
        if status_filter == "All":
            # Calculate counts
            in_progress_count = len([task for task in tasks if task['status'] == 'In progress'])
            not_started_count = len([task for task in tasks if task['status'] == 'Not started'])
            done_count = len([task for task in tasks if task['status'] == 'Done'])
            
            # Create bordered metrics using StyleHelper
            style_helper.create_bordered_metrics(
                total_tasks=len(tasks),
                in_progress=in_progress_count,
                not_started=not_started_count,
                done=done_count
            )
        else:
            st.metric(f"Filtered Tasks ({status_filter})", len(tasks))
    
    @staticmethod
    def show_footer_buttons(database_backend: str, tasks: list, task_manager: TaskManagerInterface, status_filter: str):
        """
        Display footer buttons (Refresh Tasks and Clear Tasks).
        
        Args:
            database_backend (str): Current database backend (DB_SQLITE or DB_NOTION)
            tasks (list): List of current tasks
            task_manager (TaskManagerInterface): Task manager instance
            status_filter (str): Current status filter ("All" or specific status)
        """
        if database_backend == DB_SQLITE:
            # Define filter_name at the beginning for use throughout the method
            filter_name = "All" if status_filter == "All" else f"'{status_filter}'"
            
            if not(tasks) or len(tasks) == 0:
                st.session_state.confirm_clear_all = False
            # Only show Clear button if there are tasks
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("🔄 Refresh Tasks", type="secondary", use_container_width=True):
                    st.rerun()
            with col2:
                if tasks and len(tasks) > 0:
                    # Dynamic button text based on filter
                    button_text = f"🗑️ Clear {filter_name} Tasks"
                    help_text = f"Delete all tasks with status '{filter_name}' from SQLite database"
                    
                    if st.button(button_text, type="secondary", help=help_text, use_container_width=True):
                        st.session_state.confirm_clear_all = True
                        st.rerun()
            with col3:
                pass
            with col4:
                pass
            
            # Show confirmation warning if clear button was clicked
            if st.session_state.get('confirm_clear_all', False):
                # Dynamic warning message based on filter
                warning_msg = f"⚠️ Are you sure you want to delete {filter_name} tasks? This action cannot be undone!"
                confirm_text = f"✅ Yes, Clear {filter_name}"
                spinner_text = f"Clearing {filter_name} tasks..."
                success_msg = f"✅ {filter_name} tasks have been cleared!"
                toast_msg = f"🗑️ {filter_name} tasks cleared!"
                
                st.warning(warning_msg)
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button(confirm_text, type="secondary", use_container_width=True):
                        with st.spinner(spinner_text):
                            # Call appropriate method based on filter
                            if status_filter == "All":
                                task_manager.clear_all_tasks()
                            else:
                                task_manager.clear_tasks_by_status(status_filter)
                                # Reset filter to "All" after clearing by status
                                st.session_state.status_filter_reset = "All"
                            
                            st.success(success_msg)
                            st.toast(toast_msg, icon="✅")
                            st.session_state.confirm_clear_all = False
                            st.rerun()
                with col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state.confirm_clear_all = False
                        st.rerun()
                with col3:
                    pass
                with col4:
                    pass
        else:
            # For Notion, only show refresh button
            if st.button("🔄 Refresh Tasks", type="secondary"):
                os.write(1, b"\n" + b"="*50 + b"\n")
                os.write(1, b"\xF0\x9F\x94\x84 REFRESH TASKS CLICKED (Notion)\n")
                os.write(1, b"="*50 + b"\n")
                st.rerun()
    
    @staticmethod
    def show_sync_confirmation_dialog():
        """
        Display sync confirmation dialog and handle the sync operation.
        
        This method shows a confirmation dialog when user wants to copy tasks
        from Notion to SQLite, and executes the sync if confirmed.
        """
        # Initial sync button
        if st.button("📥 Copy From Notion to SQLite", type="primary", use_container_width=True):
            st.session_state.show_sync_confirmation = True

        # Show confirmation dialog if button was clicked
        if st.session_state.get('show_sync_confirmation', False):
            st.warning("⚠️ This will replace all tasks in SQLite with tasks from Notion. Are you sure?")
            
            if st.button("✅ Yes, Sync Now", type="primary", use_container_width=True):
                st.session_state.show_sync_confirmation = False
                TaskManagerHelper._execute_sync()
        
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_sync_confirmation = False
                st.rerun()
    
    @staticmethod
    def _execute_sync():
        """
        Execute the sync operation from Notion to SQLite.
        
        This internal method handles the actual syncing process:
        - Fetches all tasks from Notion
        - Clears SQLite database
        - Copies tasks to SQLite
        """
        with st.spinner("Syncing data from Notion to SQLite..."):
            time.sleep(1)
            try:
                # Initialize both managers
                notion_manager = NotionTaskManager.get_instance()
                sqlite_manager = SqlTaskManager.get_instance()
                
                # Fetch all tasks from Notion
                notion_tasks = notion_manager.list_tasks()
                
                if notion_tasks:
                    # Clear all tasks from SQLite
                    sqlite_manager.clear_all_tasks()
                    
                    # Add all tasks from Notion to SQLite
                    success_count = 0
                    for task in notion_tasks:
                        result = sqlite_manager.add_task(task['name'], task['status'])
                        if result:
                            success_count += 1
                    
                    st.success(f"✅ Successfully synced {success_count} tasks from Notion to SQLite!")
                    st.toast(f"🎉 Synced {success_count} tasks!", icon="✅")
                    # Small delay to let the toast display before switching
                    time.sleep(1.5)
                    # Switch to SQLite backend to view synced data
                    st.session_state.selected_backend = DB_SQLITE
                    st.rerun()
                else:
                    st.warning("⚠️ No tasks found in Notion database")
                    
            except KeyError:
                st.error("❌ Notion credentials not found. Please configure .streamlit/secrets.toml")
            except Exception as e:
                st.error(f"❌ Error syncing data: {e}")
                st.toast("❌ Sync failed", icon="⚠️")

