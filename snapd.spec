#
# Conditional build:
%bcond_with	tests		# build with tests

Summary:	A transactional software package manager
Name:		snapd
Version:	2.26.1
Release:	0.1
License:	GPL v3
Group:		Base
Source0:	https://github.com/snapcore/snapd/releases/download/%{version}/%{name}_%{version}.vendor.tar.xz
# Source0-md5:	8152560d2af809ad84185d3b341b2f13
# Script to implement certain package management actions
Source1:	snap-mgmt.sh
URL:		https://github.com/snapcore/snapd
Patch0001:	0001-cmd-use-libtool-for-the-internal-library.patch
Patch0100:	%{name}-2.26.1-interfaces-seccomp-allow-bind-for-Fedora.patch
BuildRequires:	golang
BuildRequires:	systemd
BuildRequires:	tar >= 1:1.22
BuildRequires:	xz
Requires:	snap-confine = %{version}-%{release}
Requires:	squashfs-tools
# we need squashfs.ko loaded
Requires:	kmod(squashfs.ko)
# bash-completion owns /usr/share/bash-completion/completions
Requires:	bash-completion
# Force the SELinux module to be installed
Requires:	%{name}-selinux = %{version}-%{release}
ExclusiveArch:	%{ix86} %{x8664} %{arm} aarch64 ppc64le s390x
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%define		_enable_debug_packages 0
%define		gobuild(o:) go build -ldflags "${LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n')" -a -v -x %{?**};
%define		gopath		%{_libdir}/golang
%define		import_path	github.com/snapcore/snapd

%define		snappy_svcs	snapd.service snapd.socket snapd.autoimport.service snapd.refresh.timer snapd.refresh.service

%description
Snappy is a modern, cross-distribution, transactional package manager
designed for working with self-contained, immutable packages.

%package -n snap-confine
Summary:	Confinement system for snap applications
License:	GPL v3
Group:		Base
BuildRequires:	%{_bindir}/rst2man
BuildRequires:	%{_bindir}/shellcheck
BuildRequires:	autoconf
BuildRequires:	automake
BuildRequires:	gcc
BuildRequires:	gettext
BuildRequires:	glib2-devel
BuildRequires:	glibc-static
BuildRequires:	gnupg
BuildRequires:	indent
BuildRequires:	libcap-devel
BuildRequires:	libseccomp-devel
BuildRequires:	libtool
BuildRequires:	systemd-units
BuildRequires:	udev-devel
BuildRequires:	udev-devel
BuildRequires:	valgrind
BuildRequires:	xfsprogs-devel

%description -n snap-confine
This package is used internally by snapd to apply confinement to the
started snap applications.

%package selinux
Summary:	SELinux module for snapd
License:	GPL v2+
Group:		Base
BuildRequires:	selinux-policy
BuildRequires:	selinux-policy-devel
BuildArch:	noarch
Requires(post):	selinux-policy-base >= %{_selinux_policy_version}
Requires(post):	policycoreutils
Requires(post):	policycoreutils-python-utils
Requires(pre):	libselinux-utils
Requires(post):	libselinux-utils

%description selinux
This package provides the SELinux policy module to ensure snapd runs
properly under an environment with SELinux enabled.

%prep
%setup -q
%patch1 -p1
%patch100 -p1

# Generate version files
./mkversion.sh "%{version}-%{release}"

# Build snapd
mkdir -p src/github.com/snapcore
ln -s ../../../ src/github.com/snapcore/snapd

%build
export GOPATH=$(pwd):$(pwd)/Godeps/_workspace:%{gopath}

%gobuild -o bin/snap %{import_path}/cmd/snap
%gobuild -o bin/snap-exec %{import_path}/cmd/snap-exec
%gobuild -o bin/snapctl %{import_path}/cmd/snapctl
%gobuild -o bin/snapd %{import_path}/cmd/snapd
%gobuild -o bin/snap-update-ns %{import_path}/cmd/snap-update-ns

# Build SELinux module
cd data/selinux
%{__make} SHARE="%{_datadir}" TARGETS="snappy"
cd -

# Build snap-confine
cd cmd
autoreconf --force --install --verbose
# selinux support is not yet available, for now just disable apparmor
# FIXME: add --enable-caps-over-setuid as soon as possible (setuid discouraged!)
%configure \
	--disable-apparmor \
	--libexecdir=%{_libexecdir}/snapd/ \
	--with-snap-mount-dir=%{_sharedstatedir}/snapd/snap \
	--without-merged-usr

%{__make}
cd -

# Build systemd units
cd data/systemd
%{__make} \
	BINDIR="%{_bindir}" \
	LIBEXECDIR="%{_libexecdir}" \
	SNAP_MOUNT_DIR="%{_sharedstatedir}/snapd/snap" \
	SNAPD_ENVIRONMENT_FILE="%{_sysconfdir}/sysconfig/snapd"

%if %{with tests}
# snapd tests
export GOPATH=$RPM_BUILD_ROOT/%{gopath}:$(pwd)/Godeps/_workspace:%{gopath}
%gotest %{import_path}/...

# snap-confine tests (these always run!)
cd cmd
%{__make} check
cd -
%endif

%install
rm -rf $RPM_BUILD_ROOT
install -d -p $RPM_BUILD_ROOT%{_bindir}
install -d -p $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -d -p $RPM_BUILD_ROOT%{_mandir}/man1
install -d -p $RPM_BUILD_ROOT%{systemdunitdir}
install -d -p $RPM_BUILD_ROOT%{_sysconfdir}/profile.d
install -d -p $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig
install -d -p $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/assertions
install -d -p $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/desktop/applications
install -d -p $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/device
install -d -p $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/hostfs
install -d -p $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/mount
install -d -p $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/seccomp/profiles
install -d -p $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/snaps
install -d -p $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/snap/bin
install -d -p $RPM_BUILD_ROOT%{_localstatedir}/snap
install -d -p $RPM_BUILD_ROOT%{_datadir}/selinux/devel/include/contrib
install -d -p $RPM_BUILD_ROOT%{_datadir}/selinux/packages

# Install snap and snapd
install -p bin/snap $RPM_BUILD_ROOT%{_bindir}
install -p bin/snap-exec $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -p bin/snapctl $RPM_BUILD_ROOT%{_bindir}/snapctl
install -p bin/snapd $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -p bin/snap-update-ns $RPM_BUILD_ROOT%{_libexecdir}/snapd

# Install SELinux module
install -p data/selinux/snappy.if $RPM_BUILD_ROOT%{_datadir}/selinux/devel/include/contrib
install -p data/selinux/snappy.pp.bz2 $RPM_BUILD_ROOT%{_datadir}/selinux/packages

# Install snap(1) man page
bin/snap help --man > $RPM_BUILD_ROOT%{_mandir}/man1/snap.1

# Install the "info" data file with snapd version
install -D data/info $RPM_BUILD_ROOT%{_libexecdir}/snapd/info

# Install bash completion for "snap"
install -D data/completion/snap $RPM_BUILD_ROOT%{bash_compdir}/snap

# Install snap-confine
cd cmd
%{__make} install \
	DESTDIR=$RPM_BUILD_ROOT
# Undo the 0000 permissions, they are restored in the files section
chmod 0755 $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/void
# We don't use AppArmor
rm -rfv $RPM_BUILD_ROOT%{_sysconfdir}/apparmor.d
# ubuntu-core-launcher is dead
rm -fv $RPM_BUILD_ROOT%{_bindir}/ubuntu-core-launcher
cd -

# Install all systemd units
cd data/systemd
%{__make} install \
	DESTDIR=$RPM_BUILD_ROOT SYSTEMDSYSTEMUNITDIR="%{systemdunitdir}"
# Remove snappy core specific units
rm -fv $RPM_BUILD_ROOT%{systemdunitdir}/snapd.system-shutdown.service
cd -

# Put /var/lib/snapd/snap/bin on PATH
# Put /var/lib/snapd/desktop on XDG_DATA_DIRS
cat << __SNAPD_SH__ > $RPM_BUILD_ROOT%{_sysconfdir}/profile.d/snapd.sh
PATH=\$PATH:/var/lib/snapd/snap/bin
if [ -z "\$XDG_DATA_DIRS" ]; then
XDG_DATA_DIRS=%{_datadir}/:%{_prefix}/local/share/:/var/lib/snapd/desktop
else
    XDG_DATA_DIRS="\$XDG_DATA_DIRS":/var/lib/snapd/desktop
fi
export XDG_DATA_DIRS
__SNAPD_SH__

# Disable re-exec by default
echo 'SNAP_REEXEC=0' > $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/snapd

# Install snap management script
install -pm 0755 %{SOURCE1} $RPM_BUILD_ROOT%{_libexecdir}/snapd/snap-mgmt

# Create state.json file to be ghosted
touch $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/state.json

%clean
rm -rf $RPM_BUILD_ROOT

%post
%systemd_post %{snappy_svcs}
# If install, test if snapd socket and timer are enabled.
# If enabled, then attempt to start them. This will silently fail
# in chroots or other environments where services aren't expected
# to be started.
if [ $1 -eq 1 ] ; then
	if systemctl -q is-enabled snapd.socket > /dev/null 2>&1 ; then
		systemctl start snapd.socket > /dev/null 2>&1 || :
	fi
	if systemctl -q is-enabled snapd.refresh.timer > /dev/null 2>&1 ; then
		systemctl start snapd.refresh.timer > /dev/null 2>&1 || :
	fi
fi

%preun
%systemd_preun %{snappy_svcs}

# Remove all Snappy content if snapd is being fully uninstalled
if [ $1 -eq 0 ]; then
	%{_libexecdir}/snapd/snap-mgmt purge || :
fi

%postun
%systemd_postun_with_restart %{snappy_svcs}

%pre selinux
%selinux_relabel_pre

%post selinux
%selinux_modules_install %{_datadir}/selinux/packages/snappy.pp.bz2
%selinux_relabel_post

%postun selinux
%selinux_modules_uninstall snappy
if [ $1 -eq 0 ]; then
	%selinux_relabel_post
fi

%files
%defattr(644,root,root,755)
%doc COPYING
%doc README.md docs/*
%attr(755,root,root) %{_bindir}/snap
%attr(755,root,root) %{_bindir}/snapctl
%dir %{_libexecdir}/snapd
%{_libexecdir}/snapd/snapd
%{_libexecdir}/snapd/snap-exec
%{_libexecdir}/snapd/info
%{_libexecdir}/snapd/snap-mgmt
%{_mandir}/man1/snap.1*
%{bash_compdir}/snap
/etc/profile.d/snapd.sh
%{systemdunitdir}/snapd.socket
%{systemdunitdir}/snapd.service
%{systemdunitdir}/snapd.autoimport.service
%{systemdunitdir}/snapd.refresh.service
%{systemdunitdir}/snapd.refresh.timer
%config(noreplace) %verify(not md5 mtime size) /etc/sysconfig/snapd
%dir %{_sharedstatedir}/snapd
%dir %{_sharedstatedir}/snapd/assertions
%dir %{_sharedstatedir}/snapd/desktop
%dir %{_sharedstatedir}/snapd/desktop/applications
%dir %{_sharedstatedir}/snapd/device
%dir %{_sharedstatedir}/snapd/hostfs
%dir %{_sharedstatedir}/snapd/mount
%dir %{_sharedstatedir}/snapd/seccomp
%dir %{_sharedstatedir}/snapd/seccomp/profiles
%dir %{_sharedstatedir}/snapd/snaps
%dir %{_sharedstatedir}/snapd/snap
%ghost %dir %{_sharedstatedir}/snapd/snap/bin
%dir %{_localstatedir}/snap
%ghost %{_sharedstatedir}/snapd/state.json

%files -n snap-confine
%defattr(644,root,root,755)
%doc cmd/snap-confine/PORTING
%doc COPYING
%dir %{_libexecdir}/snapd
# For now, we can't use caps
# FIXME: Switch to "%%attr(0755,root,root) %%caps(cap_sys_admin=pe)" asap!
%attr(4755,root,root) %{_libexecdir}/snapd/snap-confine
%{_libexecdir}/snapd/snap-discard-ns
%{_libexecdir}/snapd/snap-update-ns
%{_libexecdir}/snapd/system-shutdown
%{_mandir}/man5/snap-confine.5*
%{_mandir}/man5/snap-discard-ns.5*
%{_prefix}/lib/udev/snappy-app-dev
%{_udevrulesdir}/80-snappy-assign.rules
%attr(0000,root,root) %{_sharedstatedir}/snapd/void

%files selinux
%defattr(644,root,root,755)
%doc data/selinux/COPYING
%doc data/selinux/README.md
%{_datadir}/selinux/packages/snappy.pp.bz2
%{_datadir}/selinux/devel/include/contrib/snappy.if
