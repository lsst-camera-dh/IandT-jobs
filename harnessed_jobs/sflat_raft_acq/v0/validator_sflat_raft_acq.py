#!/usr/bin/env python
import lcatr.schema
import siteUtils

results = []

results = siteUtils.persist_ccs_versions(results)

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
