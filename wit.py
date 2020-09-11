import datetime
import filecmp
import os
import random
import shutil
import sys

from graphviz import Digraph


COMMIT_ID_LENGTH_TO_DISPLAY_IN_GRAPH = 10


def make_dir(dir_name):
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)


def write_activated_file(wit_dir, branch_name):
    file_name = wit_dir + '\\activated.txt'
    with open(file_name, 'w') as file1:
        file1.write(f'{branch_name}\n')


def get_activated_branch(wit_dir):
    file_name = wit_dir + '\\activated.txt'
    try:
        with open(file_name, 'r') as file1:
            line = file1.readline()
            return line[: -1]
    except FileNotFoundError:
        print('\nactivated.txt file does not exist - aborting')
        sys.exit(1)


def init():
    for dir_to_create in ('.wit', '.wit\\images', '.wit\\staging_area'):
        make_dir(dir_to_create)
    write_activated_file('.wit', 'master')


def find_wit_directory():
    directory = os.getcwd()
    relative_path = ''
    while len(directory) > 0 and not os.path.exists(directory + '\\.wit'):
        i = directory.rfind('\\')
        if i > -1:
            relative_path = directory[i + 1:] + '\\' + relative_path
            directory = directory[0: i]
        else:
            print('\n".wit" directory does not exist - aborting')
            sys.exit(1)
    return directory, relative_path[:-1]


def add(filename):
    wit_dir, relative_path = find_wit_directory()
    src = wit_dir + '\\' + relative_path + '\\' + filename
    dest = wit_dir + '\\.wit\\staging_area'
    # Create relative folders which do not exist
    for folder in relative_path.split('\\'):
        dest = dest + '\\' + folder
        make_dir(dest)
    dest = dest + '\\' + filename
    try:
        if os.path.isfile(src):
            shutil.copy2(src, dest)
        else:
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest, copy_function=shutil.copy)
    except FileNotFoundError:
        print(f'\nFile {filename} does not exist - add function was ignored')


def are_dir_trees_equal(dir1, dir2):
    """
    Compare two directories recursively. Files in each directory are
    assumed to be equal if their names and contents are equal.

    @param dir1: First directory path
    @param dir2: Second directory path

    @return: True if the directory trees are the same and
        there were no errors while accessing the directories or files,
        False otherwise.
   """

    dirs_cmp = filecmp.dircmp(dir1, dir2)
    if len(dirs_cmp.left_only) > 0 or len(dirs_cmp.right_only) > 0 or len(dirs_cmp.funny_files) > 0:
        return False
    (_, mismatch, errors) = filecmp.cmpfiles(dir1, dir2, dirs_cmp.common_files, shallow=False)
    if len(mismatch) > 0 or len(errors) > 0:
        return False
    for common_dir in dirs_cmp.common_dirs:
        new_dir1 = os.path.join(dir1, common_dir)
        new_dir2 = os.path.join(dir2, common_dir)
        if not are_dir_trees_equal(new_dir1, new_dir2):
            return False
    return True


def find_commit_id_for_branch(references_file, branch_name, abort_if_file_not_found=True, not_found_msg=f'\nreferences_file does not exist - aborting'):
    try:
        with open(references_file, 'r') as file1:
            for line in file1:
                if line.split('=')[0] == branch_name:
                    return line.split('=')[1].strip()
    except FileNotFoundError:
        if not_found_msg:
            print(not_found_msg)
        if abort_if_file_not_found:
            sys.exit(1)
        else:
            return None


def get_commit_id_from_references_file(references_file, including_master=False, abort_if_file_not_found=False, not_found_msg=None):
    head_commit_id = find_commit_id_for_branch(references_file, 'HEAD', abort_if_file_not_found, not_found_msg)
    if including_master:
        master_commit_id = find_commit_id_for_branch(references_file, 'master', abort_if_file_not_found, not_found_msg)
        return head_commit_id, master_commit_id
    return head_commit_id


def set_wit_folders():
    wit_dir, relative_path = find_wit_directory()
    wit_dir = wit_dir + '\\.wit'
    images_folder = wit_dir + '\\images\\'
    stage_folder = wit_dir + '\\staging_area\\'
    references_file = wit_dir + '\\references.txt'
    return wit_dir, images_folder, stage_folder, references_file


def generate_dir_name(valid_chars, length):
    return ''.join(random.choices(valid_chars, k=length))


def modify_branch_name_in_references_file(references_file, branch_name, head_commit_id=None):
    found = False
    if not head_commit_id:
        head_commit_id = get_commit_id_from_references_file(references_file, False, True, '\nCommit was not done yet')
    line_to_modify = branch_name + '=' + head_commit_id + '\n'
    with open(references_file, 'r') as file1:
        text = file1.read()
        lines = text.split('\n')
    with open(references_file, 'w') as file1:
        for i in range(0, len(lines) - 1):
            if not lines[i].startswith(branch_name + '='):
                file1.write(lines[i] + '\n')
            else:
                found = True
                file1.write(line_to_modify)
        if not found:
            file1.write(line_to_modify)


def create_references_file(references_file, commit_id):
    with open(references_file, 'w') as file1:
        file1.write(f'HEAD={commit_id}\nmaster={commit_id}\n')


def commit(message):
    wit_dir, images_folder, stage_folder, references_file = set_wit_folders()
    # Check if commit is required, i.e. if the staging area is not equal to the previous "commit"
    prev_commit_id, master_commit_id = get_commit_id_from_references_file(references_file, True)
    if prev_commit_id:
        if are_dir_trees_equal(stage_folder, images_folder + prev_commit_id):
            print(f'\nThere is no need to perform commit - staging area is identical to last commit_id folder ({prev_commit_id}) - aborting')
            sys.exit(1)
    else:
        if len(os.listdir(stage_folder)) == 0:
            print(f'\nThere is no need to perform commit, staging area is empty - aborting')
            sys.exit(1)
        prev_commit_id = 'None'  # First time only

    commit_id = generate_dir_name('1234567890abcdef', 40)
    # Step 1 + 3: Copy the "staging_area" folder to the new generated folder
    saveset_folder = images_folder + commit_id
    shutil.copytree(stage_folder, saveset_folder, copy_function=shutil.copy)

    # Step 2 - write the metadata file
    metadata_file = images_folder + commit_id + '.txt'
    with open(metadata_file, 'w') as file1:
        current_time = datetime.datetime.now().astimezone().strftime("%a %b %d %H:%M:%S %Y %z")
        file1.write(f'parent={prev_commit_id}\ndate={current_time}\nmessage={message}\n')

    # Step 4: Updating the references.txt file
    active_branch_name = get_activated_branch(wit_dir)
    if os.path.exists(references_file):
        modify_branch_name_in_references_file(references_file, 'HEAD', commit_id)
        if find_commit_id_for_branch(references_file, active_branch_name) == prev_commit_id:  #  Active branch has same commit_id as Head so it should be updated too
            modify_branch_name_in_references_file(references_file, active_branch_name)
    else:
        create_references_file(references_file, commit_id)


def uncommited_changes(dir1, dir2, stage_folder, files, relative_path=''):
    dirs_cmp = filecmp.dircmp(dir1, dir2)
    for i in range(0, len(dirs_cmp.left_only)):
        file = relative_path + dirs_cmp.left_only[i]
        files.append(file)
        full_file_name = dir1 + '\\' + dirs_cmp.left_only[i]
        if os.path.isdir(full_file_name):
            for (dirpath, dirnames, filenames) in os.walk(full_file_name):
                dirpath = dirpath.replace('\\\\', '\\')
                for f in dirnames:
                    files.append(os.path.join(dirpath, f).replace(stage_folder, ''))
                for f in filenames:
                    files.append(os.path.join(dirpath, f).replace(stage_folder, ''))
    filecmp.cmpfiles(dir1, dir2, dirs_cmp.common_files, shallow=False)
    for common_dir in dirs_cmp.common_dirs:
        new_dir1 = os.path.join(dir1, common_dir)
        new_relative_path = new_dir1.replace(dir1, '') + '\\'
        new_dir2 = os.path.join(dir2, common_dir)
        uncommited_changes(new_dir1, new_dir2, stage_folder, files, new_relative_path)
    return files


def changes_not_staged(dir1, dir2, compare=True):
    # I implemented it in this way and not in the way written in the below commented function because this way I can get the relative path of each unequal file.
    # This way also supports the "Untracked files" search.
    files = []
    for (dirpath, _, filenames) in os.walk(dir1):
        dirpath = dirpath.replace('\\\\', '\\')
        for f in filenames:
            relative_path = dirpath.replace(dir1, '')
            file1 = os.path.join(dirpath, f)
            file2 = os.path.join(dir2, relative_path, f)
            if not os.path.exists(file2):
                file = os.path.join(relative_path, f)
                if compare:
                    file = file + '  (file was deleted from original folder but exists in staging_area)'
                if compare or not file.startswith('.wit\\'):  # All files under the .wit folder should be ignored
                    files.append(file)
            elif compare and not filecmp.cmp(file1, file2, shallow=False):
                files.append(os.path.join(relative_path, f))
    return files


'''def changes_not_staged(dcmp, files=[]):
    for name in dcmp.diff_files:
        files.append(name)

    for sub_dcmp in dcmp.subdirs.values():
        changes_not_staged(sub_dcmp)
    return files'''


def status():
    wit_dir, images_folder, stage_folder, references_file = set_wit_folders()
    commit_id = get_commit_id_from_references_file(references_file)
    print(f'\nCurrent commit id={commit_id}')
    # Print uncommited changes
    compare_folder = images_folder
    if commit_id:
        compare_folder = images_folder + commit_id

    files = uncommited_changes(stage_folder, compare_folder, stage_folder, [])
    if len(files) > 0:
        print('\nChanges to be committed:\n========================')
        print(*files, sep="\n")
    else:
        print('\nThere are no uncommited changes')

    orig_dir = wit_dir[: wit_dir.rfind('\\')]
    files = changes_not_staged(stage_folder, orig_dir)
    # dcmp = filecmp.dircmp(stage_folder, orig_dir)
    # files = changes_not_staged(dcmp)
    if len(files) > 0:
        print('\nChanges not staged for commit:\n==============================')
        print(*files, sep="\n")
    else:
        print('\nThere are no changes which are not staged for commit')

    # By turning off the "compare files" option and changing the directory to search on direction (instead of running on the staging area tree and look for the
    # files under the original tree, now I'm running on the original tree and look for each file on the staging area tree), I can use the same function as
    # for "Changes not staged for commit"
    files = changes_not_staged(orig_dir + '\\', stage_folder, compare=False)
    if len(files) > 0:
        print('\nUntracked files:\n================')
        print(*files, sep="\n")
    else:
        print('\nThere are no untracked files')


def rm(filename):
    wit_dir, relative_path = find_wit_directory()
    stage_dir = wit_dir + '\\.wit\\staging_area\\'
    file_or_dir = stage_dir + filename
    if os.path.exists(file_or_dir):
        try:
            if os.path.isfile(file_or_dir):
                os.remove(file_or_dir)
            else:
                shutil.rmtree(file_or_dir)
        except FileNotFoundError:
            print('\nFile doesn\'t exist - add function was ignored')
        except Exception as err:
            print(f'\nUnable to delete the file - {err}')
    else:
        print('\nFile not found - rm command was ignored')


def ignore_function(home_dir, ignore):
    def _ignore_(path, names):
        ignored_names = []
        for name in names:
            full_file_path = os.path.join(path, name)
            for ign in ignore:
                ign = '\\' + ign
                if full_file_path == home_dir + ign:
                    i = ign.rfind('\\')
                    ign = ign[i + 1:]
                    ignored_names.append(ign)
        return set(ignored_names)
    return _ignore_


def checkout(commit_id):
    wit_dir, images_folder, stage_folder, references_file = set_wit_folders()
    head_commit_id = get_commit_id_from_references_file(references_file, False, True, '\nCommit was not done yet so checkout cannot be executed now')
    branch_name = commit_id
    commit_id = find_commit_id_for_branch(references_file, branch_name)
    if commit_id is None:  # This is a commit_id and not a branch
        is_branch = False
        commit_id = branch_name
    else:  # This is a branch name and not a commit_id
        is_branch = True

    commit_id_folder = images_folder + commit_id
    if not os.path.exists(commit_id_folder):
        print(f'\nFolder for commit_id={commit_id} does not exist - aborting')
        sys.exit(1)

    # Check if checkout can be done - at first look for uncommited changes
    head_commit_id_folder = images_folder + head_commit_id
    files = uncommited_changes(stage_folder, head_commit_id_folder, stage_folder, [])
    if len(files) > 0:
        print('\nThere are changes to be commited - checkout cannot be done now.')
        sys.exit(1)

    # Now look for "changes not staged for commit"
    orig_dir = wit_dir[: wit_dir.rfind('\\')]
    files = changes_not_staged(stage_folder, orig_dir)
    if len(files) > 0:
        print('\nThere are changes not staged for commit - checkout cannot be done now.')
        sys.exit(1)

    files = changes_not_staged(orig_dir + '\\', stage_folder, compare=False)
    shutil.copytree(commit_id_folder, orig_dir, ignore=ignore_function(commit_id_folder, files), dirs_exist_ok=True)

    modify_branch_name_in_references_file(references_file, 'HEAD', commit_id)
    if is_branch:
        write_activated_file(wit_dir, branch_name)

    shutil.rmtree(stage_folder)
    shutil.copytree(commit_id_folder, stage_folder, copy_function=shutil.copy)


def get_parent(images_folder, commit_id):
    file = images_folder + commit_id + '.txt'
    try:
        with open(file, 'r') as file1:
            line = file1.readline()
            next_commit_id = line[7: -1]
            return next_commit_id
    except FileNotFoundError:
        print(f'\nFile {file} does not exist.')
        return 'None'  # This will cause to display the graph till now.


def graph():
    wit_dir, images_folder, stage_folder, references_file = set_wit_folders()
    commit_id, master_commit_id = get_commit_id_from_references_file(references_file, True, True, '\nCommit was not done yet so graph cannot be displayed now')
    g = Digraph('G', filename='graph_wit', format='png')
    g.attr(rankdir='RL', size='8')
    g.attr('node', shape='none')
    g.node('')
    g.attr('node', shape='circle', style='filled', fontcolor='blue')
    head_label = 'HEAD'
    prev_commit_id = ''
    if commit_id == master_commit_id:
        short_commit_id = commit_id[: COMMIT_ID_LENGTH_TO_DISPLAY_IN_GRAPH]
        g.edge(prev_commit_id, short_commit_id, label='MASTER')
    while commit_id != 'None':
        short_commit_id = commit_id[: COMMIT_ID_LENGTH_TO_DISPLAY_IN_GRAPH]
        g.edge(prev_commit_id, short_commit_id, label=head_label)
        head_label = ''
        prev_commit_id = commit_id[: COMMIT_ID_LENGTH_TO_DISPLAY_IN_GRAPH]
        commit_id = get_parent(images_folder, commit_id)
    g.view()


def branch(branch_name):
    wit_dir, images_folder, stage_folder, references_file = set_wit_folders()
    modify_branch_name_in_references_file(references_file, branch_name)


if len(sys.argv) < 2:
    print('\nNo parameters were given')
elif sys.argv[1] == 'init':
    init()
elif sys.argv[1] == 'add':
    if len(sys.argv) < 3:
        print('\nMissing at least one filename to add')
    else:
        for i in range(2, len(sys.argv)):  # In this way I can add several files in one command
            add(sys.argv[i])
elif sys.argv[1] == 'commit':
    if len(sys.argv) < 3:
        print('\nMissing message for the commit action')
    else:
        commit(sys.argv[2])
elif sys.argv[1] == 'status':
    status()
elif sys.argv[1] == 'rm':
    if len(sys.argv) < 3:
        print('\nMissing at least one filename to remove')
    else:
        for i in range(2, len(sys.argv)):  # In this way I can remove several files in one command
            rm(sys.argv[i])
elif sys.argv[1] == 'checkout':
    if len(sys.argv) < 3:
        print('\nMissing commit_id (or master) for the checkout action')
    else:
        checkout(sys.argv[2])
elif sys.argv[1] == 'graph':
    graph()
elif sys.argv[1] == 'branch':
    if len(sys.argv) < 3:
        print('\nMissing branch name')
    else:
        branch(sys.argv[2])
else:
    print('\nUnsupported function\n')
