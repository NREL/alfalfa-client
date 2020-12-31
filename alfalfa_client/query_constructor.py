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
