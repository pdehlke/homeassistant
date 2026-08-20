if [[ ! -f /.dockerenv ]]; then
	export CONTAINER_EXTRA_MOUNTS='/Users/pde/src/github.com/pdehlke/homie-dashboard'
	export HA_TOKEN='op://HomeAssistant/HA_TOKEN/password'
	export HA_EDIT_KEY='op://HomeAssistant/HA_EDIT_KEY/private key'
	export HOMIE_USERNAME='op://HomeAssistant/HOMIE_PASSWORD/username'
	export HOMIE_PASSWORD='op://HomeAssistant/HOMIE_PASSWORD/password'
	export HOMIE_TOKEN='op://HomeAssistant/HOMIE_TOKEN/password'
fi
