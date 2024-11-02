Hey all

On the pihole you will need to install the ARM Splunk Forwarder (https://www.splunk.com/en_us/download/universal-forwarder.html)

The app has an inputs for the forwarder, and props / views for the Search Head. 

Macro default for index is `index=*` and I highly recommend changing this to whatever your intended index is.

Very minimal extractions, and no CIM mapping as of yet.

Email me with any thoughts / ideas!

aaron@splunk.com
