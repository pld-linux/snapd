#
# Conditional build:
%bcond_with	tests		# build with tests
%bcond_with	selinux		# SELinux support module
%bcond_with	dynamic		# all binaries linked dynamically

Summary:	A transactional software package manager
Summary(pl.UTF-8):	Transakcyjny zarządca pakietów oprogramowania
Name:		snapd
Version:	2.65.1
Release:	0.1
License:	GPL v3
Group:		Base
#Source0Download: https://github.com/snapcore/snapd/releases
Source0:	https://github.com/snapcore/snapd/releases/download/%{version}/%{name}_%{version}.vendor.tar.xz
# Source0-md5:	7eb5aae10f38175a32d88840c21f8273
# Script to implement certain package management actions
Source1:	snap-mgmt.sh
Source2:	profile.d.sh
Source3:	%{name}.sysconfig
Patch0:		pld_is_like_fedora.patch
URL:		https://github.com/snapcore/snapd
BuildRequires:	%{_bindir}/rst2man
BuildRequires:	autoconf >= 2.69
BuildRequires:	automake
BuildRequires:	docutils
BuildRequires:	gettext-tools
BuildRequires:	glib2-devel >= 2.0
%{!?with_dynamic:BuildRequires:	glibc-static}
BuildRequires:	gnupg
BuildRequires:	golang
BuildRequires:	indent
BuildRequires:	libcap-devel
# currently disabled
#BuildRequires:	libapparmor-devel
%{!?with_dynamic:BuildRequires:	libseccomp-static}
BuildRequires:	libtool
BuildRequires:	pkgconfig
BuildRequires:	rpm-build >= 4.6
%if %{with selinux}
BuildRequires:	selinux-policy
BuildRequires:	selinux-policy-devel
%endif
BuildRequires:	systemd-devel
BuildRequires:	systemd-units
BuildRequires:	tar >= 1:1.22
BuildRequires:	udev-devel
BuildRequires:	valgrind
BuildRequires:	xfsprogs-devel
BuildRequires:	xz
Requires:	pld-release
Requires:	squashfs
Obsoletes:	snap-confine < 2.36
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

%description -l pl.UTF-8
Snappy to nowoczesny, wielodystrybucyjny, transakcyjny zarządca
pakietów zaprojektowany do pracy z samodzielnymi, niezmiennymi
pakietami.

%package selinux
Summary:	SELinux module for snapd
Summary(pl.UTF-8):	Moduł SELinuksa dla snapd
License:	GPL v2+
Group:		Base
#fix me
#Requires(post):	selinux-policy-base >= %{_selinux_policy_version}
Requires(post):	policycoreutils
Requires(post):	policycoreutils-python-utils
Requires(pre,post):	libselinux-utils
BuildArch:	noarch

%description selinux
This package provides the SELinux policy module to ensure snapd runs
properly under an environment with SELinux enabled.

%description selinux -l pl.UTF-8
Ten pakiet zawiera moduł polityki SELinuksa do zapewnienia, że snapd
działa właściwie w środowisku z włączonym SELinuksem.

%package -n bash-completion-%{name}
Summary:	Bash completion for %{name}
Summary(pl.UTF-8):	Bashowe uzupełnianie poleceń dla %{name}
Group:		Applications/Shells
Requires:	%{name} = %{version}-%{release}
Requires:	bash-completion >= 2.0
BuildArch:	noarch

%description -n bash-completion-%{name}
Bash completion for %{name}.

%description -n bash-completion-%{name} -l pl.UTF-8
Bashowe uzupełnianie poleceń dla %{name}.

%package -n zsh-completion-%{name}
Summary:	zsh completion for %{name}
Summary(pl.UTF-8):	Uzupełnianie poleceń w zsh dla %{name}
Group:		Applications/Shells
Requires:	%{name} = %{version}-%{release}
Requires:	zsh
BuildArch:	noarch

%description -n zsh-completion-%{name}
Bash completion for %{name}.

%description -n zsh-completion-%{name} -l pl.UTF-8
Uzupełnianie poleceń w zsh dla %{name}.

%prep
%setup -q
%patch0 -p1

# Generate version files
./mkversion.sh "%{version}-%{release}"

# Build snapd
mkdir -p src/github.com/snapcore
ln -s ../../../ src/github.com/snapcore/snapd

%build
export GOPATH=$(pwd):$(pwd)/vendor:%{gopath}
LDFLAGS="%{rpmldflags}"

# remove the mod file, we are building without go modules support
%{__rm} go.mod
export GO111MODULE=off

%gobuild -o bin/snap %{import_path}/cmd/snap
%gobuild -o bin/snapctl %{import_path}/cmd/snapctl
%gobuild -o bin/snapd %{import_path}/cmd/snapd
%gobuild -o bin/snap-failure %{import_path}/cmd/snap-failure

# these should be statically linked, for some reason
%if %{without dynamic}
LDFLAGS="%{rpmldflags} -static"
%endif
%gobuild -o bin/snap-update-ns %{import_path}/cmd/snap-update-ns
%gobuild -o bin/snap-exec %{import_path}/cmd/snap-exec
%gobuild -o bin/snap-seccomp %{import_path}/cmd/snap-seccomp

# back to normal
LDFLAGS="%{rpmldflags}"

%if %{with selinux}
%{__make} -C data/selinux \
	SHARE="%{_datadir}" \
	TARGETS="snappy"
%endif

# Build snap-confine
cd cmd
#autoreconf --force --install --verbose
# selinux support is not yet available, for now just disable apparmor
# FIXME: add --enable-caps-over-setuid as soon as possible (setuid discouraged!)
%{__aclocal}
%{__autoconf}
%{__autoheader}
%{__automake}
%configure \
	--disable-apparmor \
	--libexecdir=%{_libexecdir}/snapd \
	--with-snap-mount-dir=%{_sharedstatedir}/snapd/snap \
	--without-merged-usr

%{__make} \
	BINDIR="%{_bindir}" \
	LIBEXECDIR="%{_libexecdir}"
cd ..

# Build systemd units
%{__make} -C data/systemd \
	BINDIR="%{_bindir}" \
	LIBEXECDIR="%{_libexecdir}" \
	SNAP_MOUNT_DIR="%{_sharedstatedir}/snapd/snap" \
	SNAPD_ENVIRONMENT_FILE="%{_sysconfdir}/sysconfig/snapd"

%if %{with tests}
# snapd tests
export GOPATH=$RPM_BUILD_ROOT%{gopath}:$(pwd)/vendor:%{gopath}
%gotest %{import_path}/...

# snap-confine tests (these always run!)
%{__make} -C cmd check
%endif

%install
rm -rf $RPM_BUILD_ROOT
install -d $RPM_BUILD_ROOT{%{_bindir},%{_libexecdir}/snapd,%{_prefix}/lib,%{_mandir}/man1,%{systemdunitdir},/etc/profile.d,/etc/sysconfig,%{_localstatedir}/snap}
install -d $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/{assertions,desktop/applications,device,hostfs,mount,seccomp/profiles,snaps,snap/bin}

# Install snap and snapd
install -p bin/snap $RPM_BUILD_ROOT%{_bindir}
install -p bin/snap-exec $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -p bin/snapctl $RPM_BUILD_ROOT%{_bindir}/snapctl
install -p bin/snapd $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -p bin/snap-update-ns $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -p bin/snap-seccomp $RPM_BUILD_ROOT%{_libexecdir}/snapd
install -p bin/snap-failure $RPM_BUILD_ROOT%{_libexecdir}/snapd

%if %{with selinux}
install -d $RPM_BUILD_ROOT%{_datadir}/selinux/{devel/include/contrib,packages}
install -p data/selinux/snappy.if $RPM_BUILD_ROOT%{_datadir}/selinux/devel/include/contrib
install -p data/selinux/snappy.pp.bz2 $RPM_BUILD_ROOT%{_datadir}/selinux/packages
%endif

# Install snap(1) man page
bin/snap help --man > $RPM_BUILD_ROOT%{_mandir}/man1/snap.1

# Install the "info" data file with snapd version
install -Dp data/info $RPM_BUILD_ROOT%{_libexecdir}/snapd/info

# Install shell completions for "snap"
install -Dp data/completion/bash/snap $RPM_BUILD_ROOT%{bash_compdir}/snap
install -Dp data/completion/zsh/_snap $RPM_BUILD_ROOT%{zsh_compdir}/_snap

# Install snap-confine
%{__make} -C cmd install \
	LIBEXECDIR="%{_libexecdir}" \
	DESTDIR=$RPM_BUILD_ROOT
# Undo the 0000 permissions, they are restored in the files section
chmod 0755 $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/void
# We don't use AppArmor
#%{__rm} -r $RPM_BUILD_ROOT%{_sysconfdir}/apparmor.d

# Install all systemd units
%{__make} -C data/systemd install \
	DESTDIR=$RPM_BUILD_ROOT \
	LIBEXECDIR="%{_libexecdir}" \
	SYSTEMDSYSTEMUNITDIR="%{systemdunitdir}"
# Remove snappy core specific units
rm -fv $RPM_BUILD_ROOT%{systemdunitdir}/snapd.system-shutdown.service

cp -p %{SOURCE2} $RPM_BUILD_ROOT/etc/profile.d/snapd.sh
cp -p %{SOURCE3} $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/snapd

# Install snap management script
install -pm 0755 %{SOURCE1} $RPM_BUILD_ROOT%{_libexecdir}/snapd/snap-mgmt

# Create state.json file to be ghosted
touch $RPM_BUILD_ROOT%{_sharedstatedir}/snapd/state.json

# some things are still looked for in the wrong dir
%if "%{_libexecdir}" != "%{_prefix}/lib"
ln -s "%{_libexecdir}/snapd" "$RPM_BUILD_ROOT%{_prefix}/lib/snapd"
%endif

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
%doc README.md
%attr(755,root,root) %{_bindir}/snap
%attr(755,root,root) %{_bindir}/snapctl
%{_prefix}/lib/snapd
%dir %{_libexecdir}/snapd
%attr(755,root,root) %{_libexecdir}/snapd/info
%attr(6755,root,root) %{_libexecdir}/snapd/snap-confine
%attr(755,root,root) %{_libexecdir}/snapd/snap-device-helper
%attr(755,root,root) %{_libexecdir}/snapd/snap-discard-ns
%attr(755,root,root) %{_libexecdir}/snapd/snap-exec
%attr(755,root,root) %{_libexecdir}/snapd/snap-failure
%attr(755,root,root) %{_libexecdir}/snapd/snap-gdb-shim
%attr(755,root,root) %{_libexecdir}/snapd/snap-gdbserver-shim
%attr(755,root,root) %{_libexecdir}/snapd/snap-mgmt
%attr(755,root,root) %{_libexecdir}/snapd/snap-seccomp
%attr(755,root,root) %{_libexecdir}/snapd/snap-update-ns
%attr(755,root,root) %{_libexecdir}/snapd/snapd
%attr(755,root,root) %{_libexecdir}/snapd/snapd.core-fixup.sh
%attr(755,root,root) %{_libexecdir}/snapd/snapd.run-from-snap
%attr(755,root,root) %{_libexecdir}/snapd/system-shutdown
%{_mandir}/man1/snap.1*
/etc/profile.d/snapd.sh
%attr(755,root,root) /usr/lib/systemd/system-environment-generators/snapd-env-generator
%attr(755,root,root) /lib/systemd/system-generators/snapd-generator
%{systemdunitdir}/snapd.apparmor.service
%{systemdunitdir}/snapd.autoimport.service
%{systemdunitdir}/snapd.core-fixup.service
%{systemdunitdir}/snapd.failure.service
%{systemdunitdir}/snapd.recovery-chooser-trigger.service
%{systemdunitdir}/snapd.seeded.service
%{systemdunitdir}/snapd.service
%{systemdunitdir}/snapd.snap-repair.service
%{systemdunitdir}/snapd.snap-repair.timer
%{systemdunitdir}/snapd.socket
%{systemdunitdir}/snapd.mounts-pre.target
%{systemdunitdir}/snapd.mounts.target
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
%attr(0000,root,root) %{_sharedstatedir}/snapd/void
%ghost %dir %{_sharedstatedir}/snapd/snap/bin
%ghost %{_sharedstatedir}/snapd/state.json
# FIXME: FHS
%dir %{_localstatedir}/snap
%{_mandir}/man8/snapd-env-generator.8*
%{_mandir}/man8/snap-confine.8*
%{_mandir}/man8/snap-discard-ns.8*

%if %{with selinux}
%files selinux
%defattr(644,root,root,755)
%doc data/selinux/{COPYING,README.md}
%{_datadir}/selinux/packages/snappy.pp.bz2
%{_datadir}/selinux/devel/include/contrib/snappy.if
%endif

%files -n bash-completion-%{name}
%defattr(644,root,root,755)
%{bash_compdir}/snap

%files -n zsh-completion-%{name}
%defattr(644,root,root,755)
%{zsh_compdir}/_snap
