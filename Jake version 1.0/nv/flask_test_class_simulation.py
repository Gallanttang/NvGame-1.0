# This is a python script created by Jake Zhang on Oct. 15th.
# This script contains code for load-testing and class-simulation of the News Vendor Game website.
# The aim of this script is to test CPU usage on PythonAnywhere and database's capability (PAW or local) to handle concurrent comands.
# This script can only test and simulate the regular (unpaced) game mode. 
# But technically, a paced game should work fine if a regular game with the same class size and the same parameters works fine.
# The maximum class size to test and simulate is 100; the maximun round to test and simulate is 50.
# Open this script in a python IDEs, such as Spyder, and run following code after creating a session on the instructor page.
# Check the script output and User & Game tables on instructor page for test and simulation performance.
#########################################################################################################################################

# libraries
import requests
import multiprocessing as mp
#########################################################################################################################################

# initial variables
nstudent = int()
nround = int()
scode = str()
homepage_index = int()
homepage = str()

logins = list()
sessions = list()
run_responses = dict()
stats_responses = dict()
#########################################################################################################################################

# functions
def ask_input():
    global nstudent, nround, scode, homepage_index, homepage
    while True:
        try:
            nstudent = int(input('What\'s the size of the class (# of students) that you want to simulate and test: '))
            assert nstudent <= 100 and nstudent > 0
            nround = int(input('How many rounds of the game do you want to simulate and test: '))
            assert nround <= 50 and nround > 0
            scode = input('Enter the session code of the game that you want to simulate and test: ')
            homepage_index = int(input("""Enter 1 if homepage address is 'http://harishk.pythonanywhere.com'
Enter 2 if homepage address is 'http://localhost:5000'
Enter 1 or 2: """))
            assert homepage_index in [1,2]
            if homepage_index == 1:
                homepage = 'http://harishk.pythonanywhere.com'
            else: # homepage_index == 2
                homepage = 'http://localhost:5000'
            print()
            break
        except:
            print("""Please enter valid inputs for class size, number of rounds, session code, and homepage address!
Class size should be a positve integer that is less or equal to 100;
Number of rounds should be a positve integer that is less or equal to 50;\n""")
            continue

def class_prep(nstudent, nround, scode):
    global logins
    for i in range(1,nstudent+1):
        login_data = dict()
        login_data['id'] = str(99999000+i)
        login_data['pname'] = 'test'+str(i)
        login_data['scode'] = scode
        logins.append(login_data)

def session_prep_paw(login):
    s = requests.session()
    if s.post('http://harishk.pythonanywhere.com/signup', login).status_code == 200:
        return s

def session_prep_local(login):
    s = requests.session()
    if s.post('http://localhost:5000/signup', login).status_code == 200:
        return s

def mp_job_1():
    global logins, sessions, homepage_index
    pool1 = mp.Pool(processes=mp.cpu_count()-1)
    if homepage_index == 1:
        ss = (pool1.apply_async(session_prep_paw, (l,)) for l in logins)
    else: # homepage_index == 2
        ss = (pool1.apply_async(session_prep_local, (l,)) for l in logins)
    sessions = [s.get() for s in ss]
    pool1.close()
    pool1.join()
    print('Sign up done!\n')

def sim_run_stats_paw(s, day_index, student_index):
    run_sc = s.post('http://harishk.pythonanywhere.com/run', {'norder':str(student_index+1)}).status_code
    stats_sc = s.get('http://harishk.pythonanywhere.com/stats').status_code
    return (run_sc, stats_sc)

def sim_run_stats_local(s, day_index, student_index):
    run_sc = s.post('http://localhost:5000/run', {'norder':str(student_index+1)}).status_code
    stats_sc = s.get('http://localhost:5000/stats').status_code
    return (run_sc, stats_sc)

def mp_job_2():
    global sessions, homepage_index, nround, nstudent, run_responses, stats_responses
    for i in range(1, nround+1):
        pool2 = mp.Pool(processes=mp.cpu_count()-1)
        if homepage_index == 1:
            scs = (pool2.apply_async(sim_run_stats_paw, (sessions[j], i, j)) for j in range(nstudent))
        else: # homepage_index == 2
            scs = (pool2.apply_async(sim_run_stats_local, (sessions[j], i, j)) for j in range(nstudent))
        round_res = [sc.get() for sc in scs]
        pool2.close()
        pool2.join()
        run_responses[i] = [t[0] for t in round_res]
        stats_responses[i] = [t[1] for t in round_res]
        print('Round {} done!\n'.format(i))
#########################################################################################################################################

# run
if __name__ == '__main__':
    # ask for input
    ask_input()
    # prepare login info
    class_prep(nstudent, nround, scode)
    # mp login
    mp_job_1()
    # performance - login
    print("""Total of {} students in class: 
{} students successfully signed up;
{} students failed to signed up;\n""".format(nstudent, len(sessions), nstudent-len(sessions)))
    # mp run & stats
    mp_job_2()
    # performance - run & stats
    for i in range(1, nround+1):
        run_200_rate = round(run_responses[i].count(200)/len(run_responses[i])*100,2)
        stats_200_rate = round(stats_responses[i].count(200)/len(stats_responses[i])*100,2)
        print("""Round{}: websites successfully loaded for {}% of all students in RUN step;
Round{}: websites successfully loaded for {}% of all students in STATS step;\n""".format(i,run_200_rate,i,stats_200_rate))