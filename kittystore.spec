%global pypi_name KittyStore
#%%global prerel 1

Name:           kittystore
Version:        0.1.7
Release:        %{?prerel:0.}1%{?dist}
Summary:        A storage engine for GNU Mailman v3 archives

License:        GPLv3
URL:            https://fedorahosted.org/hyperkitty/
Source0:        http://pypi.python.org/packages/source/K/%{pypi_name}/%{pypi_name}-%{version}%{?prerel:dev}.tar.gz

BuildArch:      noarch
BuildRequires:  python-devel

BuildRequires:  python-nose
BuildRequires:  python-mock
BuildRequires:  python-dateutil < 2.0
BuildRequires:  python-storm
BuildRequires:  python-zope-interface
BuildRequires:  python-networkx
#BuildRequires:  mailman >= 3:3.0.0
BuildRequires:  mailman3
BuildRequires:  python-whoosh
BuildRequires:  python-mailman-client
BuildRequires:  python-dogpile-cache
Requires:  python-mock
Requires:  python-dateutil < 2.0
Requires:  python-storm
Requires:  python-zope-interface
Requires:  python-networkx
#Requires:  mailman >= 3:3.0.0
Requires:  mailman3
Requires:  python-whoosh
Requires:  python-mailman-client
Requires:  python-dogpile-cache

%description
KittyStore is the archiving library for HyperKitty, the Mailman 3 archiver.
It provides an interface to different storage systems. Currently only the
Storm ORM system is supported.

The code is available from:
https://github.com/hyperkitty/kittystore


%prep
%setup -q -n %{pypi_name}-%{version}%{?prerel:dev}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info


%build
%{__python} setup.py build


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install --skip-build --root %{buildroot}

%check
%{__python} %{_bindir}/nosetests
#%{__python} setup.py test

%files
%doc README.rst COPYING.txt AUTHORS.txt
%{_bindir}/kittystore-*
%{python_sitelib}/kittystore
%{python_sitelib}/%{pypi_name}-%{version}%{?prerel:dev}-py?.?.egg-info


%changelog
* Wed Nov 28 2012 Aurelien Bompard <abompard@fedoraproject.org> - 0.1.3
- initial package
