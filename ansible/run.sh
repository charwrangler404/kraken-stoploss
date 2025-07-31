#!/usr/bin/env sh

## Set inventory to the first option
inventory="${1}"

## Give options if none passed
if [ -z "$#" ]; then
    echo "Usage:"
    echo "${0} <inventory_file"
    exit 0
fi

## If $END is unspecified by the environment, or is not a number,
## then set a default value that allows interaction
if [ -z "${END}" || ! ${END} =~ '^[0-9]+$' ]; then
    END=10
fi

## Do you wish to set a root password?
read -p "Do you wish to set a secure root password value for the machine? [y/N]: " answer

## Does the user want it?
if [ "${answer}" =~ '^[yY]' ]; then
    ## Get hash
    root_hash=$(mkpasswd -m sha-512)

    ## Create the sed script
    cat > /tmp/hash.sed <<EOF
s/root_password_hash:.?$/root_password_hash: ${root_hash}/
EOF

    ## Modify the secrets.yml file
    sed -i -s /tmp/hash.sed vars/secrets.yml

    ## clean up after ourselves
    rm /tmp/hash.sed
fi

## Check for whether or not $DESTORY_DATABASE_VOLUME is set
if [ "$DESTROY_DATABASE_VOLUME" -eq "true" ]; then
    read -p "Are you sure you wish to destroy the database volume? [y/N]" answer
    ## Ask if they're sure
    if [ ${answer} =~ '^[yY]' ]; then
        echo "Choice ${answer} confirmed, running without volume task"
        ## Run the playbook
        ansible-playbook -i "${inventory}" playbooks/no_destroy_volume.yml
        exit $?
    else
        ## Give them one last chance to opt out
        echo "Choice ${answer} confirmed, continuing with database volume destruction"
        echo "You may cancel in the next ${END} seconds with ctrl+c"
        for i in {1..${END}}; do
            echo -n "${i}."
            sleep 1
        done
        ## Run the playbook
        echo "\nExecuting playbook with database volume destruction"
        ansible-playbook -i "${inventory}" playbooks/yes_destroy_volume.yml
        exit $?
    fi
fi