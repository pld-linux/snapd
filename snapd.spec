#
# Conditional build:
%bcond_with	tests		# build with tests
%bcond_with	selinux		# selinux

Summary:	A transactional software package manager
Name:		snapd
Version:	2.42.5
Release:	1
License:	GPL v3
Group:		Base
Source0:	https://github.com/snapcore/snapd/releases/download/%{version}/%{name}_%{version}.vendor.tar.xz
# Source0-md5:	9c6a50f07b33587519f2d1e0656c5f6f
# Script to implement certain package management actions
Source1:	snap-mgmt.sh
Source2:	profile.d.sh
Source3:	%{name}.sysconfig
Patch0:		pld_is_like_fedora.patch
URL:		https://github.com/snapcore/snapd
BuildRequires:	%{_bindir}/rst2man
BuildRequires:	autoconf
BuildRequires:	automake
BuildRequires:	gcc
BuildRequires:	gettext
BuildRequires:	glib2-devel
BuildRequires:	glibc-static
BuildRequires:	gnupg
BuildRequires:	golang
BuildRequires:	indent
BuildRequires:	libcap-devel
BuildRequires:	libseccomp-static
BuildRequires:	libtool
BuildRequires:	pkgconfig
BuildRequires:	systemd-devel
BuildRequires:	systemd-units
BuildRequires:	tar >= 1:1.22
BuildRequires:	udev-devel
BuildRequires:	valgrind
BuildRequires:	xfsprogs-devel
BuildRequires:	xz
Requires:	pld-release
Requires:	squashfs
Obsoletes:	snap-confine
ExclusiveArch:	%{ix86} %{x8664} %{arm} aarch64 ppc64le s390x
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%define		_udevrulesdir /lib/udev/rules.d

%define		_enable_debug_packages 0
%define		gobuild(o:) go build -ldflags "-extldflags '${LDFLAGS:-}' -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n')" -a -v -x %{?**};
%define		gopath		%{_libdir}/golang
%define		import_path	github.com/snapcore/snapd

%define		snappy_svcs	snapd.service snapd.socket snapd.apparmor.service snapd.core-fixup.service snapd.failure.service snapd.seeded.service snapd.autoimport.service snapd.snap-repair.timer

%description
Snappy is a modern, cross-distribution, transactional package manager
designed for working with self-contained, immutable packages.

%package selinux
Summary:	SELinux module for snapd
License:	GPL v2+
Group:		Base
%if %{with selinux}
BuildRequires:	selinux-policy
BuildRequires:	selinux-policy-devel
%endif
Requires(post):	selinux-policy-base >= %{_selinux_policy_version}
Requires(post):	policycoreutils
Requires(post):	policycoreutils-python-utils
Requires(pre):	libselinux-utils
Requires(post):	libselinux-utils
BuildArch:	noarch

%description selinux
This package provides the SELinux policy module to ensure snapd runs
properly under an environment with SELinux enabled.

%package -n bash-completion-%{name}
Summary:	bash-completion for %{name}
Group:		Applications/Shells
Requires:	%{name} = %{version}-%{release}
Requires:	bash-completion
BuildArch:	noarch

%description -n bash-completion-%{name}
bash-completion for %{name}.

%prep
%setup -q
%patch0 -p1

# Generate version files
./mkversion.sh "%{version}-%{release}"

# Build snapd
mkdir -p src/github.com/snapcore
ln -s ../../../ src/github.com/snapcore/snapd

%build
export GOPATH=$(pwd):$(pwd)/Godeps/_workspace:%{gopath}

LDFLAGS="%{rpmldflags}"
%gobuild -o bin/snap %{import_path}/cmd/snap
%gobuild -o bin/snapctl %{import_path}/cmd/snapctl
%gobuild -o bin/snapd %{import_path}/cmd/snapd
%gobuild -o bin/snap-failure %{import_path}/cmd/snap-failure

# these should be statically linked, for some reason
LDFLAGS="%{rpmldflags} -static"
%gobuild -o bin/snap-update-ns %{import_path}/cmd/snap-update-ns
%gobuild -o bin/snap-exec %{import_path}/cmd/snap-exec
%gobuild -o bin/snap-seccomp %{import_path}/cmd/snap-seccomp

# back to normal
LDFLAGS="%{rpmldflags}"

%if %{with selinux}
cd data/selinux
%{__make} SHARE="%{_datadir}" TARGETS="snappy"
cd -
%endif

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

%{__make} \
	BINDIR="%{_bindir}" \
	LIBEXECDIR="%{_libexecdir}"
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
install -d -p $RPM_BUILD_ROOT/etc/profile.d
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
install -d -p $RPM_BUILD_ROOT%{_prefix}/lib

# Install snap and snapd
install -p bin/snap $RPM_BUILD_ROOT%{_bindir}
install -p bin/snap-exec $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -p bin/snapctl $RPM_BUILD_ROOT%{_bindir}/snapctl
install -p bin/snapd $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -p bin/snap-update-ns $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -p bin/snap-seccomp $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -p bin/snap-failure $RPM_BUILD_ROOT%{_libexecdir}/snapd

%if %{with selinux}
install -d -p $RPM_BUILD_ROOT%{_datadir}/selinux/devel/include/contrib
install -d -p $RPM_BUILD_ROOT%{_datadir}/selinux/packages
install -p data/selinux/snappy.if $RPM_BUILD_ROOT%{_datadir}/selinux/devel/include/contrib
install -p data/selinux/snappy.pp.bz2 $RPM_BUILD_ROOT%{_datadir}/selinux/packages
%endif

# Install snap(1) man page
bin/snap help --man > $RPM_BUILD_ROOT%{_mandir}/man1/snap.1

# Install the "info" data file with snapd version
install -D data/info $RPM_BUILD_ROOT%{_libexecdir}/snapd/info

# Install bash completion for "snap"
install -D data/completion/snap $RPM_BUILD_ROOT%{bash_compdir}/snap

# Install snap-confine
cd cmd
%{__make} install \
	LIBEXECDIR="%{_libexecdir}" \
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
	LIBEXECDIR="%{_libexecdir}" \
	DESTDIR=$RPM_BUILD_ROOT SYSTEMDSYSTEMUNITDIR="%{systemdunitdir}"
# Remove snappy core specific units
rm -fv $RPM_BUILD_ROOT%{systemdunitdir}/snapd.system-shutdown.service
cd -

cp -p %{SOURCE2} $RPM_BUILD_ROOT/etc/profile.d/snapd.sh
cp -p %{SOURCE3} $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/snapd

# Install snap management script
install -pm 0755 %{SOURCE1} $RPM_BUILD_ROOT%{_libexecdir}/snapd/snap-mgmt

# Create state.json file to be ghosted
touch $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/state.json

# some things are still looked for in the wrong dir
ln -s "%{_libexecdir}/snapd" "$RPM_BUILD_ROOT%{_prefix}/lib/snapd"

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
	if systemctl -q is-enabled snapd.snap-repair.timer > /dev/null 2>&1 ; then
		systemctl start snapd.snap-repair.timer > /dev/null 2>&1 || :
	fi
fi

%preun
%systemd_preun %{snappy_svcs}

# Remove all Snappy content if snapd is being fully uninstalled
if [ $1 -eq 0 ]; then
	%{_libexecdir}/snapd/snap-mgmt purge || :
fi

%postun
%systemd_reload

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
%doc README.md docs/*
%attr(755,root,root) %{_bindir}/snap
%attr(755,root,root) %{_bindir}/snapctl
%{_prefix}/lib/snapd
%dir %{_libexecdir}/snapd
%attr(755,root,root) %{_libexecdir}/snapd/info
%attr(6755,root,root) %{_libexecdir}/snapd/snap-confine
%attr(755,root,root) %{_libexecdir}/snapd/snapd
%attr(755,root,root) %{_libexecdir}/snapd/snapd.core-fixup.sh
%attr(755,root,root) %{_libexecdir}/snapd/snap-device-helper
%attr(755,root,root) %{_libexecdir}/snapd/snap-discard-ns
%attr(755,root,root) %{_libexecdir}/snapd/snapd.run-from-snap
%attr(755,root,root) %{_libexecdir}/snapd/snap-exec
%attr(755,root,root) %{_libexecdir}/snapd/snap-failure
%attr(755,root,root) %{_libexecdir}/snapd/snap-gdb-shim
%attr(755,root,root) %{_libexecdir}/snapd/snap-mgmt
%attr(755,root,root) %{_libexecdir}/snapd/snap-seccomp
%attr(755,root,root) %{_libexecdir}/snapd/snap-update-ns
%attr(755,root,root) %{_libexecdir}/snapd/system-shutdown
%{_mandir}/man1/snap.1*
/etc/profile.d/snapd.sh
%attr(755,root,root) /usr/lib/systemd/system-environment-generators/snapd-env-generator
%attr(755,root,root) %{systemdunitdir}-generators/snapd-generator
%{systemdunitdir}/snapd.apparmor.service
%{systemdunitdir}/snapd.core-fixup.service
%{systemdunitdir}/snapd.failure.service
%{systemdunitdir}/snapd.seeded.service
%{systemdunitdir}/snapd.snap-repair.service
%{systemdunitdir}/snapd.snap-repair.timer
%{systemdunitdir}/snapd.socket
%{systemdunitdir}/snapd.service
%{systemdunitdir}/snapd.autoimport.service
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
%{_mandir}/man8/snapd-env-generator.8*
%{_mandir}/man8/snap-confine.8*
%{_mandir}/man8/snap-discard-ns.8*
%attr(0000,root,root) %{_sharedstatedir}/snapd/void

%if %{with selinux}
%files selinux
%defattr(644,root,root,755)
%doc data/selinux/COPYING
%doc data/selinux/README.md
%{_datadir}/selinux/packages/snappy.pp.bz2
%{_datadir}/selinux/devel/include/contrib/snappy.if
%endif

%files -n bash-completion-%{name}
%defattr(644,root,root,755)
%{bash_compdir}/snap
