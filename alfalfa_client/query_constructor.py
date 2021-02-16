"""
****************************************************************************************************
:copyright (c) 2008-2021 URBANopt, Alliance for Sustainable Energy, LLC, and other contributors.

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions
and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this list of conditions
and the following disclaimer in the documentation and/or other materials provided with the
distribution.

Neither the name of the copyright holder nor the names of its contributors may be used to endorse
or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
****************************************************************************************************
"""
class QueryConstructor:

    # GraphQL queries
    @staticmethod
    def inputs(site_id):
        return 'query { viewer { sites(siteRef: "%s") { points(writable: true) { dis tags { key value } } } } }' % site_id

    @staticmethod
    def outputs(site_id):
        return 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % site_id

    @staticmethod
    def all_cur_points(site_id):
        return 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % site_id

    @staticmethod
    def all_cur_points_with_units(site_id):
        return 'query { viewer { sites(siteRef: "%s") { points(cur: true) { dis tags { key value } } } } }' % site_id

    @staticmethod
    def get_sim_time(site_id):
        return 'query { viewer { sites(siteRef: "%s") { datetime } } }' % site_id

    @staticmethod
    def all_writable_points(site_id):
        return 'query { viewer { sites(siteRef: "%s") { points(writable: true) { dis tags { key value } } } } }' % site_id

    @staticmethod
    def all_cur_writable_points(site_id):
        return 'query { viewer { sites(siteRef: "%s") { points(writable: true, cur: true) { dis tags { key value } } } } }' % site_id

    # Haystack queries
    # TODO: look into pyhaystack Filter builder
    @staticmethod
    def get_read_site_points(site_id):
        return f"siteRef==@{site_id} and point and cur and not equipRef"

    @staticmethod
    def get_write_site_points(site_id):
        return f"siteRef==@{site_id} and point and writable and not equipRef"

    @staticmethod
    def get_read_write_site_points(site_id):
        return f"siteRef==@{site_id} and point and writable and cur and not equipRef"

    @staticmethod
    def get_thermal_zones(site_id):
        return f"siteRef==@{site_id} and zone"

    @staticmethod
    def get_points(site_id):
        return f"siteRef==@{site_id} and point"
