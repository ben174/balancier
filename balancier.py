#!/usr/bin/env python

import logging

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


class KwargInitMixin(object):
    def __init__(self, *args, **kwargs):
        '''
        Initialize an object setting all properties from kwargs, useful for
        consuming CSVs
        '''
        for key, val in kwargs.items():
            setattr(self, key, val)


class Facility(KwargInitMixin):
    def __init__(self, *args, **kwargs):
        super(Facility, self).__init__(*args, **kwargs)
        self.bank = None
        self.banned_states = []
        self.max_default_likelihood = None
        self.interest_rate = float(self.interest_rate)
        self.assigned_loans = []
        self.amount = float(self.amount)

    @property
    def effective_banned_states(self):
        '''
        Gets all effective banned states from parent bank as well as facility
        '''
        return self.banned_states + self.bank.banned_states

    @property
    def effective_max_default_likelihood(self):
        '''
        Gets the smallest maximum default likelihood from parent bank as well as facility
        '''
        if self.bank.max_default_likelihood and self.max_default_likelihood:
            return min(self.max_default_likelihood, self.bank.max_default_likelihood)
        return self.bank.max_default_likelihood or self.max_default_likelihood

    def validate_loan(self, loan):
        '''
        Validates that there are no covenants in place which would restrict this loan
        from originating.
        '''
        if loan.state in self.effective_banned_states:
            logging.debug('Invalid due to originating state: {}, Banned States: {}'.format(
                loan.state,
                self.effective_banned_states,
            ))
            return False
        if loan.default_likelihood > self.effective_max_default_likelihood:
            logging.debug('Invalid due to default likelihood: {}, Max likelihood: {}'.format(
                loan.default_likelihood,
                self.effective_max_default_likelihood,
            ))
            return False
        if loan.amount > self.amount:
            logging.debug('Invalid due insufficient facility funds: {}, Loan amount: {}'.format(
                self.amount,
                loan.amount,
            ))
            return False
        logging.debug('Facility is valid.')
        return True

    def calculate_yield_for_loan(self, loan):
        '''
        Calculates expected yield if the loan were assigned to this facility
        '''
        expected_yield = ((1. - loan.default_likelihood) * loan.interest_rate * loan.amount
                          - loan.default_likelihood * loan.amount
                          - self.interest_rate * loan.amount)
        return expected_yield

    def calculate_total_yield(self):
        '''
        Returns projected yield for all loans assigned to the facility, rounded to the nearest
        penny.
        '''
        total = 0
        for loan in self.assigned_loans:
            total += loan.expected_yield
        return int(round(total))

    def assign_loan(self, loan, expected_yield):
        '''
        Assigns the specified loan to this facility
        '''
        self.assigned_loans.append(loan)
        loan.assigned_facility = self
        loan.expected_yield = expected_yield
        self.amount -= loan.amount

    def __str__(self):
        return 'Facility: {}, Amount: {}, Loans: {}, Total Yield: {}'.format(
            self.id,
            self.amount,
            len(self.assigned_loans),
            self.calculate_total_yield(),
        )


class Bank(KwargInitMixin):
    def __init__(self, *args, **kwargs):
        super(Bank, self).__init__(*args, **kwargs)
        self.facilities = []
        self.banned_states = []
        self.max_default_likelihood = None


class Covenant(KwargInitMixin):
    def __init__(self, *args, **kwargs):
        super(Covenant, self).__init__(*args, **kwargs)
        self.bank = None
        self.facility = None


class Loan(KwargInitMixin):
    def __init__(self, *args, **kwargs):
        super(Loan, self).__init__(*args, **kwargs)
        self.assigned_facility = None
        self.expected_yield = None
        self.amount = float(self.amount)
        self.default_likelihood = float(self.default_likelihood)
        self.interest_rate = float(self.interest_rate)

    def assign(self, facilities):
        '''
        Searches through all provided facilities finding the best one to assign the loan to.
        '''
        max_yield = None
        selected_facility = None
        for facility in facilities:
            logging.debug('Validating facility: {}'.format(facility.id))
            if not facility.validate_loan(self):
                logging.debug(' - Facility is invalid')
            else:
                expected_yield = facility.calculate_yield_for_loan(self)
                logging.debug(' - Expected yield: {}'.format(expected_yield))
                if not expected_yield or expected_yield > max_yield:
                    max_yield = expected_yield
                    selected_facility = facility
                    logging.debug(' - Best facility so far: {}, amount: {}, expected yield: {}'.format(
                        selected_facility.id,
                        self.amount,
                        self.expected_yield
                    ))
                else:
                    logging.debug(' - Not optimal')
        if not selected_facility:
            logging.warning('Unable to assign loan: {}, Amount: {}'.format(self.id, self.amount))
            return
        selected_facility.assign_loan(self, max_yield)
        return facility

    def __str__(self):
        return 'Loan {}, Assigned: {}, Amount: {}'.format(
            self.id,
            self.assigned_facility.id if self.assigned_facility else 'X',
            self.amount,
        )


class Balancier(object):
    def __init__(self):
        self.covenants, self.banks, self.loans, self.facilities = [], [], [], []
        self.assignments, self.yields = [], []
        self.bank_table, self.facility_table = {}, {}

    def read_data(self, directory):
        files = [
                    (Bank, 'banks.csv', self.banks),
                    (Covenant, 'covenants.csv', self.covenants),
                    (Facility, 'facilities.csv', self.facilities),
                    (Loan, 'loans.csv', self.loans),
                ]
        for (klass, filename, collection) in files:
            lines = open('./{}/{}'.format(directory, filename)).readlines()
            fields = lines.pop(0).strip().split(',')
            for line in lines:
                kwargs = dict(zip(fields, line.strip().split(',')))
                collection.append(klass(**kwargs))

    def normalize_data(self):
        for bank in self.banks:
            self.bank_table[bank.id] = bank

        for facility in self.facilities:
            self.facility_table[facility.id] = facility
            facility.bank = self.bank_table[facility.bank_id]
            facility.bank.facilities.append(facility)

        for covenant in self.covenants:
            covenant.bank = self.bank_table[covenant.bank_id]
            if covenant.facility_id:
                covenant.facility = self.facility_table[covenant.facility_id]

            # assign this covenant to its facility or bank
            entity = covenant.facility or covenant.bank
            if covenant.banned_state:
                entity.banned_states.append(covenant.banned_state)
            if covenant.max_default_likelihood:
                # take the smallest max_default_likelihood from all covenants
                if (entity.max_default_likelihood is None or
                        entity.max_default_likelihood < covenant.max_default_likelihood):
                    entity.max_default_likelihood = covenant.max_default_likelihood

    def make_assignments(self):
        for loan in self.loans:
            logging.debug('Assigning loan: {}'.format(loan.id))
            loan.assign(self.facilities)

    def write_assignments(self):
        f = open('assignment_ben.csv', 'w')
        f.write('loan_id,facility_id\n')
        for loan in self.loans:
            if not loan.assigned_facility:
                logging.warning('Loan ID: {} was not assigned.'.format(loan.id))
                continue
            logging.info('Loan ID: {} assigned to: {}'.format(loan.id, loan.assigned_facility.id))
            f.write('{},{}\n'.format(loan.id, loan.assigned_facility.id))
        f.flush()
        f.close()

    def write_yields(self):
        f = open('yields_ben.csv', 'w')
        f.write('facility_id,expected_yield\n')
        for facility in self.facilities:
            logging.info('Facility ID: {} yielded: {}'.format(facility.id, facility.calculate_total_yield()))
            f.write('{},{}\n'.format(facility.id, facility.calculate_total_yield()))
        f.flush()
        f.close()

    def log_status(self):
        logging.info('Facility Status:')
        for facility in self.facilities:
            logging.info(str(facility))
        logging.info('Loan Status:')
        for loan in self.loans:
            logging.info(str(loan))
        logging.info('Unassigned Loans:')
        for loan in self.loans:
            if not loan.assigned_facility:
                logging.info(str(loan))


if __name__ == '__main__':
    balancier = Balancier()
    balancier.read_data('large')
    balancier.normalize_data()
    balancier.make_assignments()
    balancier.write_assignments()
    balancier.write_yields()
    balancier.log_status()
