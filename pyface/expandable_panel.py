# Copyright (c) 2017, Enthought, Inc.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in enthought/LICENSE.txt and may be redistributed only
# under the conditions described in the aforementioned license.  The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
# Thanks for using Enthought open source!

# Note: The ExpandablePanel is currently wx-specific

# Import the toolkit specific version.


from .toolkit import toolkit_object
ExpandablePanel = toolkit_object('expandable_panel:ExpandablePanel')
