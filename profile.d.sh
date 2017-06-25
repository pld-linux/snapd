
# Put /var/lib/snapd/snap/bin on PATH
# Put /var/lib/snapd/desktop on XDG_DATA_DIRS

PATH=$PATH:/var/lib/snapd/snap/bin
if [ -z "$XDG_DATA_DIRS" ]; then
	XDG_DATA_DIRS=/usr/share:/usr/local/share:/var/lib/snapd/desktop
else
    XDG_DATA_DIRS="$XDG_DATA_DIRS":/var/lib/snapd/desktop
fi
export XDG_DATA_DIRS
