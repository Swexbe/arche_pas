 #!/bin/bash
 #You need lingua and gettext installed to run this
 
 echo "Updating arche_pas.pot"
 pot-create -d arche_pas -o arche_pas/locale/arche_pas.pot arche_pas/.
 echo "Merging Swedish localisation"
 msgmerge --update  arche_pas/locale/sv/LC_MESSAGES/arche_pas.po  arche_pas/locale/arche_pas.pot
 echo "Updated locale files"
