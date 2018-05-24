# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2018 CZ.NIC, z.s.p.o. <http://www.nic.cz>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

BRAND ?= turris

COMPILED_CSS = $(wildcard foris/static/css/*)

COMPILED_L10N = $(wildcard foris/locale/*/LC_MESSAGES/*.mo)

PRE_TPL_FILES = $(wildcard \
	foris/templates/*.pre.tpl \
	foris/templates/**/*.pre.tpl \
)

TPL_FILES = $(PRE_TPL_FILES:.pre.tpl=.tpl)

SASS_COMPILER = compass compile -s compressed -e production


all: branding sass localization tpl

# target: tpl - Do preprocessing of .pre.tpl files.
tpl: $(PRE_TPL_FILES) $(TPL_FILES)

# target: branding - Copy assets for a specified device to its location.
branding:
	@echo "-- Preparing branding for '$(BRAND)'"
	@[ -d branding/$(BRAND) ] || (echo "Directory with '$(BRAND)' branding does not exist" && exit 1)
	@cp -fr branding/$(BRAND)/. foris/static/
	@echo

# target: sass - Compile SASS files to CSS files using SASS/Compass compiler.
sass:
	@cd foris/static/; \
	echo '-- Running compass $<';\
	$(SASS_COMPILER)
	@echo

# target: localization - Create .mo files from .po fiels in locale directory
localization:
	@echo "-- Compiling localization files"
	@tools/compilemessages.sh foris
	@echo "Done."
	@echo

%.tpl: %.pre.tpl
	@echo '-- Preprocessing template $<'
	tools/preprocess_template.sh $< > $@
	@echo

# target: clean - Remove all compiled CSS and localization files.
clean:
	rm -rf $(COMPILED_CSS) $(COMPILED_L10N) $(TPL_FILES)

# target: help - Show this help.
help:
	@egrep "^# target:" Makefile

.PHONY: all branding sass localization tpl
