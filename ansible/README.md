# Ansible playbook for server configuration

## A word of warning about the volume task

The volumes task creates, formats, and mounts volumes on your machine. It's expected that the influxdb database
lives on it's own volume, preferably ssd storage. This will vastly impact the performance of the whole app, and
is *highly* recommended. It is not suggested that you store this volume on the root disk. This allows influxdb
to have exclusive bandwidth for the database, and if you want to make fast actions, this is very recommended.

Creating and formatting volumes is an **inherently destructive** action, and therefore this task should only
be performed on the first run, or if you do not care about your database. By default this task will only be 
performed once, and the file responsible for allowing this to run will be removed for future runs.

**IF YOU SHOOT YOURSELF IN THE FOOT WITH THIS, THIS IS YOUR FAULT**

You should **NEVER** enable the influx-volume task on successive runs unless you **WISH TO DESTROY** your influx
install and database volume.

## A note about Security

As we are talking about access to your kraken account api keys with this playbook, you should be very careful 
and read as much of the playbook you can and *ensure you understand what is happening*. We are human developers 
and humans make mistakes. Be very careful with your api keys, as they can be used to make trades and transfer 
funds. We do not wish for you to lose your crypto. Take care. Be safe. Read the code, and the documentation fully
before deciding to give this software your api key. If you decide not to trust this playbook, that's fine. Move the
vars/secrets.example.yml to vars/secrets.yml and do not fill in the `kraken_api_key` field. Install your api key 
manually. We will provide examples on how to do this at a later date.

Also, because of how this program is written, it is *not recommended* that you run the playbook manually. Use our
wrapper script, it will ensure that you don't accidentally wipe your database or expose your kraken api keys by
leaving them on a hard drive. We recommend never storing your api keys to your crypto accounts *anywhere* you don't
*expressly need to*. Not in a password vault, not on your hard drive, not in your email, not in a text file, nowhere. 
As long as you maintain access to your kraken account, you should be able to create a new api key. Unfortunately,
your api key *must* be available to the software this playbook installs, (that is, on the machine you are running 
this script against) so you should take every effort to *guard that key like it's worth all the money in your kraken 
account*, because, well, it is. If you don't trust us, fine. Don't. That's your choice. Find another piece of software,
or write your own. We won't be upset about this. At the end of the day, you must take responsibility for your own 
financial wellbeing.

## A note about SSH keys

SSH keys are access to the server, and thus access to your api key, and thus access to your kraken account balance.
**Password protect them for the love of all that is holy**. Or, if you don't believe anything is holy, password
protect them for the love of your own money. We recommend following the 
[NIST Password Guidelines](https://pages.nist.gov/800-63-4/sp800-63b/passwords/) at the very **minimum**. Ideally, the
password on your key should be 50-100% *longer* than what's recommended in these guidelines. Yes, this is a pain.
Yes, it's necessary. If you ever lose your key, or worse, accidentally send it to someone, or worse, have it stolen
from you, you *should* still be safe if you password protect it, but it depends entirely on the strength of your 
password.

## Variables

Before running this playbook, make sure to fill in the empty variables in the vars/main.yml and vars/secrets.yml
files. These files contain the variables that will define the behavior of this playbook. They are expected and
necessary for proper behavior of the playbook.

## Server requirements

Recommended server setup is the latest version of Debian stable, but you could probably get away with Ubuntu as 
well. We have not, nor will we, field questions about Ubuntu. Just use Debian if you have questions. That's what
this is tested on, and that is what we will answer questions about.

Current VPS setup:

    1 core shared cpu with 10gb root volume and 10gb database volume with snapshots enabled

Database size:

    At this time, unknown, likely variable. 10gb volume is what we are testing, but this may need to be expanded

## Setup

To set up the environment necessary for this playbook, you can run the install.sh file. Like any code you run on 
your computer, you should make sure you trust it. Read it, preferrably *before* you execute it.

    chmod u+x install.sh
    ./install.sh

## Running the playbook

**First time you run this playbook *only***

    DESTROY_DATABASE_VOLUME=true ./run.sh


**Subsequent runs of the playbook**

    ./run.sh
    
Good luck, and happy tuning.
